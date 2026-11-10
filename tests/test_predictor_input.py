import cv2
import numpy as np

from inference.predictor import prepare_image


def _png(arr):
    return cv2.imencode(".png", arr)[1].tobytes()


def test_contract_image_has_no_flags():
    rng = np.random.default_rng(0)
    img = prepare_image(_png(rng.integers(0, 255, (200, 200), dtype=np.uint8)))
    assert img.gray.shape == (200, 200) and img.flags == []


def test_resized_input_flagged():
    img = prepare_image(_png(np.random.default_rng(1).integers(0, 255, (480, 640), dtype=np.uint8)))
    assert img.gray.shape == (200, 200) and "resized_from_640x480" in img.flags


def test_gray_stored_as_rgb_not_flagged_as_colour():
    g = np.random.default_rng(2).integers(0, 255, (200, 200), dtype=np.uint8)
    img = prepare_image(_png(np.dstack([g, g, g])))
    assert img.flags == []


def test_true_colour_flagged():
    rng = np.random.default_rng(3)
    img = prepare_image(_png(rng.integers(0, 255, (200, 200, 3), dtype=np.uint8)))
    assert "colour_image_converted_to_gray" in img.flags


def test_uniform_image_flagged():
    assert "near_uniform_image" in prepare_image(_png(np.full((200, 200), 128, np.uint8))).flags


def test_garbage_bytes_raise():
    import pytest
    with pytest.raises(ValueError):
        prepare_image(b"not an image")
