from pathlib import Path


def viewer_source() -> str:
    return (Path(__file__).parents[1] / "visualization" / "viewer.html").read_text(
        encoding="utf-8"
    )


def test_viewer_has_stable_layout_state_and_force_release() -> None:
    viewer = viewer_source()
    assert '<option value="stable">Stable</option>' in viewer
    assert "function fixCurrentPositions()" in viewer
    assert "node.fx=node.x" in viewer
    assert "node.fy=node.y" in viewer
    assert "function releaseFixedPositions()" in viewer
    assert "delete node.fx" in viewer
    assert "delete node.fy" in viewer


def test_viewer_supports_pointer_dragging_and_force_release() -> None:
    viewer = viewer_source()
    assert "canvas.onpointerdown" in viewer
    assert "canvas.onpointermove" in viewer
    assert "canvas.onpointerup" in viewer
    assert "canvas.setPointerCapture" in viewer
    assert "node.x=node.fx" in viewer
    assert "node.y=node.fy" in viewer
    assert "ui.layout.value!=='stable'" in viewer


def test_hidden_transitive_links_can_be_excluded_from_force_layout() -> None:
    viewer = viewer_source()
    assert 'id="hidden-force" type="checkbox" checked' in viewer
    assert "function forceEdges()" in viewer
    assert "ui.reduction.checked&&!ui['hidden-force'].checked?reductionEdges()" in viewer
    assert "ui['hidden-force'].onchange=restartForceMotion" in viewer
