"""Local viewer server with restricted experiment and result APIs."""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
import threading
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from scn_sorting.algorithms.initial import ALGORITHMS
from scn_sorting.experiments.export_distribution import build_document

LABEL_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")


def is_project_root(path: Path) -> bool:
    return (
        (path / "pyproject.toml").is_file()
        and (path / "visualization" / "distributions.html").is_file()
        and (path / "src" / "scn_sorting").is_dir()
    )


def find_project_root(start: Path) -> Path | None:
    for candidate in (start.resolve(), *start.resolve().parents):
        if is_project_root(candidate):
            return candidate
    return None


def available_sizes(root: Path) -> list[int]:
    sizes = []
    for path in (root / "data" / "generated").glob("permutations-n*.jsonl.gz"):
        match = re.fullmatch(r"permutations-n(\d+)\.jsonl\.gz", path.name)
        if match:
            sizes.append(int(match.group(1)))
    return sorted(set(sizes))


def inspect_summary(root: Path, path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    relative = path.relative_to(root).as_posix()
    return {
        "name": path.stem.removesuffix("-summary"),
        "path": relative,
        "url": "/api/distribution?path=" + relative,
        "algorithms": sorted({row["algorithm"] for row in rows}),
        "sizes": sorted({int(row["n"]) for row in rows}),
        "trials": sorted({int(row["trials"]) for row in rows}),
        "modified": datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat(),
        "bytes": path.stat().st_size,
    }


def discover_results(root: Path) -> list[dict[str, object]]:
    results = []
    for path in (root / "data" / "results").rglob("*-summary.csv"):
        try:
            results.append(inspect_summary(root, path))
        except (KeyError, OSError, ValueError):
            continue
    return sorted(results, key=lambda item: str(item["modified"]), reverse=True)


def resolve_result(root: Path, relative: str) -> Path:
    results_root = (root / "data" / "results").resolve()
    path = (root / relative).resolve()
    if results_root not in path.parents or not path.name.endswith("-summary.csv"):
        raise ValueError("result must be a summary CSV under data/results")
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


@dataclass
class Job:
    identifier: str
    command: list[str]
    label: str
    status: str = "queued"
    return_code: int | None = None
    log: list[str] = field(default_factory=list)
    result_path: str | None = None

    def public(self) -> dict[str, object]:
        return {
            "id": self.identifier,
            "command": self.command,
            "label": self.label,
            "status": self.status,
            "return_code": self.return_code,
            "log": self.log[-200:],
            "result_path": self.result_path,
        }


class ProjectService:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.jobs: dict[str, Job] = {}
        self.lock = threading.Lock()

    def set_root(self, path: str) -> None:
        candidate = Path(path).expanduser().resolve()
        if not is_project_root(candidate):
            raise ValueError("folder is not an SCN sorting experiment project root")
        self.root = candidate

    def project(self) -> dict[str, object]:
        return {
            "root": str(self.root),
            "algorithms": sorted(ALGORITHMS),
            "sizes": available_sizes(self.root),
        }

    def start_job(self, request: dict[str, object]) -> Job:
        algorithms = request.get("algorithms")
        sizes = request.get("sizes")
        first_seed = request.get("first_seed")
        last_seed = request.get("last_seed")
        label = request.get("label")
        if not isinstance(algorithms, list) or not algorithms:
            raise ValueError("select at least one algorithm")
        if any(name not in ALGORITHMS for name in algorithms):
            raise ValueError("request contains an unknown algorithm")
        valid_sizes = set(available_sizes(self.root))
        if not isinstance(sizes, list) or not sizes or any(size not in valid_sizes for size in sizes):
            raise ValueError("select input sizes with generated datasets")
        if not isinstance(first_seed, int) or not isinstance(last_seed, int):
            raise TypeError("seed bounds must be integers")
        if not 1 <= first_seed <= last_seed <= 1000:
            raise ValueError("seed range must satisfy 1 <= first <= last <= 1000")
        if not isinstance(label, str) or not LABEL_PATTERN.fullmatch(label):
            raise ValueError("label may contain letters, numbers, dots, hyphens, and underscores")
        summary = self.root / "data" / "results" / f"batch-{label}-summary.csv"
        raw = self.root / "data" / "results" / f"batch-{label}-runs.jsonl.gz"
        if summary.exists() or raw.exists():
            raise FileExistsError("that label already has result files; choose a new label")
        with self.lock:
            if any(job.status in {"queued", "running"} for job in self.jobs.values()):
                raise RuntimeError("an experiment is already running")
            command = [
                sys.executable,
                "-m", "scn_sorting.experiments.batch",
                "--algorithms", *algorithms,
                "--sizes", *(str(size) for size in sizes),
                "--first-seed", str(first_seed),
                "--last-seed", str(last_seed),
                "--label", label,
            ]
            job = Job(uuid.uuid4().hex, command, label)
            self.jobs[job.identifier] = job
        threading.Thread(target=self._run_job, args=(job,), daemon=True).start()
        return job

    def _run_job(self, job: Job) -> None:
        job.status = "running"
        try:
            process = subprocess.Popen(
                job.command, cwd=self.root, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, bufsize=1,
            )
            assert process.stdout is not None
            for line in process.stdout:
                job.log.append(line.rstrip())
            job.return_code = process.wait()
            job.status = "completed" if job.return_code == 0 else "failed"
            result = self.root / "data" / "results" / f"batch-{job.label}-summary.csv"
            if job.status == "completed" and result.is_file():
                job.result_path = result.relative_to(self.root).as_posix()
        except OSError as error:  # pragma: no cover - defensive process boundary
            job.status = "failed"
            job.log.append(f"Server error: {error}")
            job.return_code = -1


class ViewerServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], service: ProjectService):
        super().__init__(address, ViewerHandler)
        self.service = service


class ViewerHandler(SimpleHTTPRequestHandler):
    server: ViewerServer

    def send_json(self, value: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        payload = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def read_json(self) -> dict[str, object]:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 64_000:
            raise ValueError("request is too large")
        value = json.loads(self.rfile.read(length))
        if not isinstance(value, dict):
            raise TypeError("request body must be an object")
        return value

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/project":
                self.send_json(self.server.service.project())
                return
            if parsed.path == "/api/results":
                self.send_json({"results": discover_results(self.server.service.root)})
                return
            if parsed.path == "/api/distribution":
                relative = parse_qs(parsed.query).get("path", [""])[0]
                self.send_json(build_document(resolve_result(self.server.service.root, relative)))
                return
            if parsed.path.startswith("/api/jobs/"):
                identifier = parsed.path.rsplit("/", 1)[-1]
                job = self.server.service.jobs.get(identifier)
                self.send_json(job.public() if job else {"error": "job not found"}, HTTPStatus.OK if job else HTTPStatus.NOT_FOUND)
                return
        except (FileNotFoundError, ValueError) as error:
            self.send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
            return
        self.directory = str(self.server.service.root / "visualization")
        super().do_GET()

    def do_POST(self) -> None:
        try:
            request = self.read_json()
            if self.path == "/api/project":
                path = request.get("path")
                if not isinstance(path, str):
                    raise ValueError("path must be a string")
                self.server.service.set_root(path)
                self.send_json(self.server.service.project())
                return
            if self.path == "/api/run":
                self.send_json(self.server.service.start_job(request).public(), HTTPStatus.ACCEPTED)
                return
            self.send_json({"error": "API endpoint not found"}, HTTPStatus.NOT_FOUND)
        except (FileExistsError, RuntimeError) as error:
            self.send_json({"error": str(error)}, HTTPStatus.CONFLICT)
        except (json.JSONDecodeError, TypeError, ValueError) as error:
            self.send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--root", type=Path)
    arguments = parser.parse_args()
    root = arguments.root.resolve() if arguments.root else find_project_root(Path.cwd())
    if root is None or not is_project_root(root):
        parser.error("project root was not found; provide --root /path/to/project")
    server = ViewerServer(("127.0.0.1", arguments.port), ProjectService(root))
    print(f"Project root: {root}")
    print(f"Open: http://127.0.0.1:{arguments.port}/distributions.html")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
