"""Synthetic sales data for the demo.

All values come from a seeded random generator. The data is not real.
"""

from __future__ import annotations

import csv
import io
import random

COLUMNS = ["month", "region", "product", "units", "unit_price", "revenue"]
MONTHS = 12
YEAR = 2025
REGIONS = ("North", "South", "East", "West")
PRODUCTS = {
    "Basic plan": 19.0,
    "Team plan": 49.0,
    "Enterprise plan": 199.0,
}


def make_sales_csv(seed: int = 7) -> str:
    """Return one year of synthetic monthly sales as CSV text."""
    rng = random.Random(seed)
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(COLUMNS)
    for month in range(1, MONTHS + 1):
        for region in REGIONS:
            for product, base_price in PRODUCTS.items():
                # A small growth trend each month, with random noise.
                units = max(0, int(rng.gauss(100 + 8 * month, 25)))
                unit_price = round(base_price * rng.uniform(0.9, 1.05), 2)
                revenue = round(units * unit_price, 2)
                writer.writerow(
                    [f"{YEAR}-{month:02d}", region, product, units, unit_price, revenue]
                )
    return buffer.getvalue()
