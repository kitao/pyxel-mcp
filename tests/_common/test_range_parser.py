import pytest
from pyxel_mcp.observe._harnesses._common.range_parser import resolve_frames, RangeError


# Explicit list cases
def test_explicit_list_passthrough():
    assert resolve_frames([10, 20, 30], total_frames=100) == ([10, 20, 30], False)


def test_explicit_list_sorted_and_dedup():
    out, normalized = resolve_frames([60, 30, 30, 90], total_frames=100)
    assert out == [30, 60, 90]
    assert normalized is True


# Range strings
def test_range_string_basic():
    out, normalized = resolve_frames("0:5", total_frames=100)
    assert out == [0, 1, 2, 3, 4]
    assert normalized is False


def test_range_string_with_step():
    out, normalized = resolve_frames("0:10:2", total_frames=100)
    assert out == [0, 2, 4, 6, 8]
    assert normalized is False


def test_range_string_all():
    out, normalized = resolve_frames("all", total_frames=5)
    assert out == [0, 1, 2, 3, 4]
    assert normalized is False


# Invalid input
@pytest.mark.parametrize("bad", [
    ":10",            # open-ended
    "10:",            # open-ended
    ":",              # both ends open
    "0:5:0",          # step = 0
    "0:5:-1",         # negative step
    "5:5",            # start == end (empty range)
    "10:5",           # start > end
    "abc",            # gibberish
    "0:abc",          # partial
])
def test_invalid_range_strings_raise(bad):
    with pytest.raises(RangeError):
        resolve_frames(bad, total_frames=100)


def test_out_of_bounds_raises():
    with pytest.raises(RangeError):
        resolve_frames("0:101", total_frames=100)
    with pytest.raises(RangeError):
        resolve_frames([5, 99, 200], total_frames=100)
    with pytest.raises(RangeError):
        resolve_frames([-1], total_frames=100)
