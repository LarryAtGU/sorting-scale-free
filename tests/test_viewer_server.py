from __future__ import annotations

import csv
from pathlib import Path

import pytest

from scn_sorting.viewer_server import (
    ProjectService,
    available_sizes,
    discover_results,
    find_project_root,
    is_project_root,
    resolve_result,
)


def make_project(root: Path) -> None:
    (root / "visualization").mkdir(parents=True)
    (root / "visualization" / "distributions.html").write_text("dashboard")
    (root / "src" / "scn_sorting").mkdir(parents=True)
    (root / "pyproject.toml").write_text("[project]\nname='test'\n")
    (root / "data" / "generated").mkdir(parents=True)
    (root / "data" / "results").mkdir(parents=True)


def test_project_root_discovery_and_generated_sizes(tmp_path: Path) -> None:
    make_project(tmp_path)
    nested = tmp_path / "src" / "scn_sorting"
    for n in (512, 128):
        (tmp_path / "data" / "generated" / f"permutations-n{n}.jsonl.gz").touch()
    assert is_project_root(tmp_path)
    assert find_project_root(nested) == tmp_path
    assert available_sizes(tmp_path) == [128, 512]


def test_result_discovery_and_path_confinement(tmp_path: Path) -> None:
    make_project(tmp_path)
    summary = tmp_path / "data" / "results" / "nested" / "batch-pilot-summary.csv"
    summary.parent.mkdir()
    with summary.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["algorithm", "n", "trials"])
        writer.writeheader()
        writer.writerow({"algorithm": "quick", "n": 128, "trials": 10})
    results = discover_results(tmp_path)
    assert results[0]["path"] == "data/results/nested/batch-pilot-summary.csv"
    assert results[0]["algorithms"] == ["quick"]
    assert resolve_result(tmp_path, results[0]["path"]) == summary
    with pytest.raises(ValueError, match="under data/results"):
        resolve_result(tmp_path, "pyproject.toml")


def test_experiment_request_is_restricted(tmp_path: Path) -> None:
    make_project(tmp_path)
    (tmp_path / "data" / "generated" / "permutations-n128.jsonl.gz").touch()
    service = ProjectService(tmp_path)
    base = {
        "algorithms": ["quick"],
        "sizes": [128],
        "first_seed": 1,
        "last_seed": 2,
        "label": "pilot",
    }
    with pytest.raises(ValueError, match="unknown algorithm"):
        service.start_job({**base, "algorithms": ["not-a-command"]})
    with pytest.raises(ValueError, match="generated datasets"):
        service.start_job({**base, "sizes": [999]})
    with pytest.raises(ValueError, match="label"):
        service.start_job({**base, "label": "../outside"})
