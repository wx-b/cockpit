"""Tests for ``backboard.cockpit.py``."""

import pytest

from backboard.cockpit import Cockpit
from backpack.extensions import BatchGrad, BatchGradTransforms, DiagGGNExact


def test_merge_batch_grad_transforms():
    """Test merging of multiple ``BatchGradTransforms``."""
    bgt1 = BatchGradTransforms({"x": lambda t: t, "y": lambda t: t})
    bgt2 = BatchGradTransforms({"v": lambda t: t, "w": lambda t: t})

    merged_bgt = Cockpit._merge_batch_grad_transforms([bgt1, bgt2])
    assert isinstance(merged_bgt, BatchGradTransforms)

    merged_keys = ["x", "y", "v", "w"]
    assert len(merged_bgt.get_transforms().keys()) == len(merged_keys)

    for key in merged_keys:
        assert key in merged_bgt.get_transforms().keys()

    assert id(bgt1.get_transforms()["x"]) == id(merged_bgt.get_transforms()["x"])
    assert id(bgt2.get_transforms()["w"]) == id(merged_bgt.get_transforms()["w"])


def test_merge_batch_grad_transforms_same_key_fails():
    """Test merging of multiple ``BatchGradTransforms`` with overlapping keys fails."""
    bgt1 = BatchGradTransforms({"x": lambda t: t, "y": lambda t: t})
    bgt2 = BatchGradTransforms({"x": lambda t: t, "w": lambda t: t})

    with pytest.raises(ValueError):
        _ = Cockpit._merge_batch_grad_transforms([bgt1, bgt2])


def test_process_multiple_batch_grad_transforms_empty():
    """Test processing if no ``BatchGradTransforms`` is used."""
    ext1 = BatchGrad()
    ext2 = DiagGGNExact()

    extensions = [ext1, ext2]
    processed = Cockpit._process_multiple_batch_grad_transforms(extensions)

    assert processed == extensions
