"""Tests for the synthetic image and the multimodal questions."""

import io

from PIL import Image

from decisions_demo.sample_image import make_delivery_slip, multimodal_questions


def test_slip_is_a_valid_png():
    data = make_delivery_slip()

    image = Image.open(io.BytesIO(data))
    assert image.format == "PNG"
    assert image.size[0] >= 600


def test_slip_is_the_same_every_time():
    assert make_delivery_slip() == make_delivery_slip()


def test_multimodal_questions_types():
    questions = multimodal_questions()

    assert questions["is_missed_delivery_slip"]["type"] == "noul"
    assert questions["tracking_number_visible"]["type"] == "noul"
    assert questions["next_step"]["type"] == "choice"
    assert questions["legibility"]["type"] == "score"
