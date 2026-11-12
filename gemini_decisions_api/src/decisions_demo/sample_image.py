"""A synthetic missed-delivery slip image, and the questions about it.

The code draws the image with Pillow, so the repository holds no image file and the
image has no copyright problem.
"""

from __future__ import annotations

import io

from PIL import Image, ImageDraw, ImageFont

from decisions_demo.questions import Question, choice, noul, score

SLIP_LINES = [
    "EXAMPLE PARCEL CO.",
    "SORRY WE MISSED YOU",
    "",
    "Date: 10 Nov    Time: 14:20",
    "Tracking no: AB123456789XX",
    "Slip no: DA-48213",
    "",
    "Your parcel is too large for the letterbox.",
    "[x] Collect at a locker after 18:00 tomorrow",
    "[ ] We will try again tomorrow",
]


def make_delivery_slip() -> bytes:
    """Return a PNG image of a synthetic missed-delivery slip. The bytes are the same each time."""
    image = Image.new("RGB", (720, 420), color=(250, 245, 225))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=22)
    draw.rectangle([(10, 10), (709, 409)], outline=(200, 30, 30), width=4)
    y = 30
    for line in SLIP_LINES:
        draw.text((40, y), line, fill=(20, 20, 20), font=font)
        y += 36
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=False)
    return buffer.getvalue()


def multimodal_questions() -> dict[str, Question]:
    """Return several questions about one image. One request asks all of them."""
    return {
        "is_missed_delivery_slip": noul("The image shows a missed-delivery slip."),
        "tracking_number_visible": noul("A parcel tracking number is readable in the image."),
        "next_step": choice(
            "What does the slip tell the customer to do?",
            {
                "collect_at_locker": "Collect the parcel at a locker.",
                "wait_for_redelivery": "Wait for a second delivery attempt.",
                "pay_a_fee": "Pay a fee before delivery.",
                "unclear": "The slip does not say.",
            },
        ),
        "legibility": score(
            "How easy is the slip to read?",
            ["Not readable.", "Partly readable.", "Fully readable."],
        ),
    }
