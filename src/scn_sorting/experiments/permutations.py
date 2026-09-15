"""Version-stable deterministic generation of uniform random permutations.

The implementation intentionally owns its PRNG and shuffle instead of relying on
Python's module-level random state. Given the same generator version, ``n``, and
trial seed, it produces the same permutation on every supported machine.
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final

MASK64: Final = (1 << 64) - 1
UINT64_RANGE: Final = 1 << 64
DOMAIN_SEPARATOR: Final = 0x53434E5F5045524D  # ASCII-like marker: SCN_PERM
GENERATOR_NAME: Final = "splitmix64-fisher-yates"
GENERATOR_VERSION: Final = "1"
PRODUCTION_SIZES: Final = (128, 256, 512, 1024, 2048, 4096)
PRODUCTION_SEEDS: Final = range(1, 1001)


class SplitMix64:
    """Small, fully specified 64-bit pseudorandom number generator."""

    def __init__(self, state: int) -> None:
        self._state = state & MASK64

    def next_uint64(self) -> int:
        """Return the next unsigned 64-bit output."""
        self._state = (self._state + 0x9E3779B97F4A7C15) & MASK64
        value = self._state
        value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
        value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & MASK64
        return (value ^ (value >> 31)) & MASK64

    def randbelow(self, bound: int) -> int:
        """Sample uniformly from ``range(bound)`` using rejection sampling."""
        if not 1 <= bound <= UINT64_RANGE:
            raise ValueError("bound must be between 1 and 2**64 inclusive")
        limit = UINT64_RANGE - (UINT64_RANGE % bound)
        while True:
            candidate = self.next_uint64()
            if candidate < limit:
                return candidate % bound


def _validate_parameters(n: int, seed: int) -> None:
    if isinstance(n, bool) or not isinstance(n, int) or not 1 <= n <= 0xFFFFFFFF:
        raise ValueError("n must be an integer between 1 and 2**32 - 1")
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= 0xFFFFFFFF:
        raise ValueError("seed must be an integer between 0 and 2**32 - 1")


def _initial_state(n: int, seed: int) -> int:
    _validate_parameters(n, seed)
    return DOMAIN_SEPARATOR ^ (n << 32) ^ seed


def generate_permutation(n: int, seed: int) -> tuple[int, ...]:
    """Generate the deterministic permutation identified by ``(n, seed)``."""
    generator = SplitMix64(_initial_state(n, seed))
    values = list(range(n))
    for index in range(n - 1, 0, -1):
        swap_index = generator.randbelow(index + 1)
        values[index], values[swap_index] = values[swap_index], values[index]
    return tuple(values)


def validate_permutation(permutation: Sequence[int], n: int) -> None:
    """Raise ``ValueError`` unless the sequence is exactly a permutation of range(n)."""
    if len(permutation) != n:
        raise ValueError(f"expected length {n}, received {len(permutation)}")
    seen = bytearray(n)
    for value in permutation:
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"permutation value is not an integer: {value!r}")
        if not 0 <= value < n:
            raise ValueError(f"permutation value outside [0, {n - 1}]: {value}")
        if seen[value]:
            raise ValueError(f"duplicate permutation value: {value}")
        seen[value] = 1


def permutation_digest(permutation: Sequence[int]) -> str:
    """Return a canonical SHA-256 digest including length and ordered values."""
    validate_permutation(permutation, len(permutation))
    digest = hashlib.sha256()
    digest.update(len(permutation).to_bytes(8, "big", signed=False))
    for value in permutation:
        digest.update(value.to_bytes(4, "big", signed=False))
    return digest.hexdigest()


def find_duplicate_permutations(permutations: Iterable[Sequence[int]]) -> list[tuple[int, int]]:
    """Return index pairs containing identical permutations.

    Digests are used only as a pre-screen. Full tuples are compared before a
    duplicate is reported, so a digest collision cannot create a false match.
    """
    candidates: dict[str, list[tuple[int, tuple[int, ...]]]] = {}
    duplicates: list[tuple[int, int]] = []
    for index, permutation in enumerate(permutations):
        frozen = tuple(permutation)
        digest = permutation_digest(frozen)
        for earlier_index, earlier in candidates.get(digest, []):
            if frozen == earlier:
                duplicates.append((earlier_index, index))
        candidates.setdefault(digest, []).append((index, frozen))
    return duplicates


@dataclass(frozen=True)
class DatasetManifest:
    schema_version: int
    generator: str
    generator_version: str
    n: int
    first_seed: int
    last_seed: int
    sequence_count: int
    data_file: str
    data_sha256: str


def write_dataset(output_directory: Path | str, n: int, seeds: Iterable[int]) -> DatasetManifest:
    """Write a reproducible gzip JSON-lines dataset and its manifest."""
    seed_values = tuple(seeds)
    if not seed_values:
        raise ValueError("at least one seed is required")
    if len(set(seed_values)) != len(seed_values):
        raise ValueError("seed identifiers must be unique")
    for seed in seed_values:
        _validate_parameters(n, seed)

    output_path = Path(output_directory)
    output_path.mkdir(parents=True, exist_ok=True)
    data_path = output_path / f"permutations-n{n}.jsonl.gz"
    manifest_path = output_path / f"permutations-n{n}.manifest.json"

    seen_digests: dict[str, int] = {}
    with (
        data_path.open("wb") as raw_stream,
        gzip.GzipFile(filename="", mode="wb", fileobj=raw_stream, mtime=0) as gzip_stream,
        io.TextIOWrapper(gzip_stream, encoding="utf-8", newline="\n") as stream,
    ):
        for seed in seed_values:
            permutation = generate_permutation(n, seed)
            validate_permutation(permutation, n)
            digest = permutation_digest(permutation)
            earlier_seed = seen_digests.get(digest)
            if earlier_seed is not None:
                earlier = generate_permutation(n, earlier_seed)
                if permutation == earlier:
                    data_path.unlink(missing_ok=True)
                    raise ValueError(
                        "duplicate generated permutations for seeds "
                        f"{earlier_seed} and {seed}"
                    )
            else:
                seen_digests[digest] = seed
            row = {"n": n, "seed": seed, "permutation": permutation}
            stream.write(json.dumps(row, separators=(",", ":")))
            stream.write("\n")

    data_digest = hashlib.sha256(data_path.read_bytes()).hexdigest()
    manifest = DatasetManifest(
        schema_version=1,
        generator=GENERATOR_NAME,
        generator_version=GENERATOR_VERSION,
        n=n,
        first_seed=min(seed_values),
        last_seed=max(seed_values),
        sequence_count=len(seed_values),
        data_file=data_path.name,
        data_sha256=data_digest,
    )
    manifest_path.write_text(json.dumps(asdict(manifest), indent=2) + "\n", encoding="utf-8")
    return manifest


def read_dataset(data_path: Path | str) -> list[tuple[int, int, tuple[int, ...]]]:
    """Read and validate a generated gzip JSON-lines dataset."""
    records: list[tuple[int, int, tuple[int, ...]]] = []
    with gzip.open(Path(data_path), "rt", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            row = json.loads(line)
            try:
                n = row["n"]
                seed = row["seed"]
                permutation = tuple(row["permutation"])
                _validate_parameters(n, seed)
                validate_permutation(permutation, n)
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError(f"invalid dataset row {line_number}: {error}") from error
            records.append((n, seed, permutation))
    return records
