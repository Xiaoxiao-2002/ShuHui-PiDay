import pytest

from shuhui.errors import TopologyError
from shuhui.topology import build_circle_pack, build_classic


def test_classic_topology_counts_and_stable_ids():
    topology = build_classic(2, 3)
    assert len(topology.vertices) == 12
    assert len(topology.edges) == 17
    assert len(topology.cells) == 6
    assert topology.cells["cell:1:2"].edge_ids == ("h:1:2", "v:1:3", "h:2:2", "v:1:2")


def test_circle_triangle_topology_and_sectors():
    topology = build_circle_pack([2, 1])
    assert len(topology.vertices) == 15
    assert len(topology.edges) == 18
    assert len(topology.cells) == 4
    triangles = [cell for cell in topology.cells.values() if cell.kind == "triangle"]
    assert len(triangles) == 1
    assert len(triangles[0].edge_ids) == 3
    assert {topology.edges[f"arc:0:0:{index}"].sector for index in range(6)} == set(range(6))


@pytest.mark.parametrize("profile", [[3, 4, 3], [2, 3, 4, 3, 2], [4, 3, 4, 5]])
def test_arbitrary_valid_profiles(profile):
    topology = build_circle_pack(profile)
    assert sum(cell.kind == "circle" for cell in topology.cells.values()) == sum(profile)


@pytest.mark.parametrize("profile", [[], [0], [2, 2], [2, 4]])
def test_invalid_profiles(profile):
    with pytest.raises(TopologyError):
        build_circle_pack(profile)

