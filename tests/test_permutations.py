from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from scn_sorting.experiments.permutations import (
    PRODUCTION_SIZES,
    SplitMix64,
    find_duplicate_permutations,
    generate_permutation,
    permutation_digest,
    read_dataset,
    validate_permutation,
    write_dataset,
)


def test_splitmix64_reference_vector() -> None:
    generator = SplitMix64(0)
    assert [generator.next_uint64() for _ in range(3)] == [
        0xE220A8397B1DCDAF,
        0x6E789E6AA1B965F4,
        0x06C45D188009454F,
    ]


@pytest.mark.parametrize("n", [1, 2, 3, 16, *PRODUCTION_SIZES])
@pytest.mark.parametrize("seed", [1, 2, 999, 1000])
def test_generated_values_are_valid_permutations(n: int, seed: int) -> None:
    permutation = generate_permutation(n, seed)
    validate_permutation(permutation, n)
    assert sorted(permutation) == list(range(n))


def test_generation_is_reproducible_and_returns_immutable_tuple() -> None:
    first = generate_permutation(128, 41)
    second = generate_permutation(128, 41)
    assert isinstance(first, tuple)
    assert first == second


def test_seed_and_size_both_separate_streams() -> None:
    assert generate_permutation(128, 1) != generate_permutation(128, 2)
    assert generate_permutation(128, 1) != generate_permutation(129, 1)[:128]


def test_permutation_known_answer() -> None:
    # Locks the public (n, seed) mapping against accidental implementation drift.
    assert generate_permutation(10, 1) == (6, 8, 0, 9, 4, 1, 3, 2, 7, 5)


def test_validation_rejects_invalid_sequences() -> None:
    with pytest.raises(ValueError, match="length"):
        validate_permutation((0, 1), 3)
    with pytest.raises(ValueError, match="duplicate"):
        validate_permutation((0, 1, 1), 3)
    with pytest.raises(ValueError, match="outside"):
        validate_permutation((0, 1, 3), 3)
    with pytest.raises(TypeError, match="not an integer"):
        validate_permutation((0, 1, "2"), 3)  # type: ignore[arg-type]


def test_digest_is_reproducible_and_order_sensitive() -> None:
    first = generate_permutation(16, 1)
    second = generate_permutation(16, 2)
    assert permutation_digest(first) == permutation_digest(first)
    assert permutation_digest(first) != permutation_digest(second)


def test_duplicate_detection_confirms_full_sequences() -> None:
    first = generate_permutation(16, 1)
    second = generate_permutation(16, 2)
    assert find_duplicate_permutations([first, second, first]) == [(0, 2)]


def test_first_thousand_small_test_sequences_have_no_duplicates() -> None:
    permutations = (generate_permutation(16, seed) for seed in range(1, 1001))
    assert find_duplicate_permutations(permutations) == []


def test_dataset_round_trip_and_manifest(tmp_path: Path) -> None:
    manifest = write_dataset(tmp_path, 16, range(1, 11))
    data_path = tmp_path / manifest.data_file
    records = read_dataset(data_path)

    assert manifest.generator == "splitmix64-fisher-yates"
    assert manifest.generator_version == "1"
    assert manifest.sequence_count == 10
    assert records == [
        (16, seed, generate_permutation(16, seed)) for seed in range(1, 11)
    ]
    assert manifest.data_sha256 == hashlib.sha256(data_path.read_bytes()).hexdigest()


def test_dataset_rejects_duplicate_seed_identifiers(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="seed identifiers must be unique"):
        write_dataset(tmp_path, 16, [1, 1])


@pytest.mark.parametrize(
    ("n", "seed"),
    [(0, 1), (-1, 1), (True, 1), (10, -1), (10, True)],
)
def test_invalid_generation_parameters_are_rejected(n: int, seed: int) -> None:
    with pytest.raises(ValueError):
        generate_permutation(n, seed)
