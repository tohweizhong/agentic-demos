"""Tests for the synthetic sales data."""

import csv
import io

from managed_agents_demo import data


def rows(text: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(text)))


def test_columns_and_row_count():
    text = data.make_sales_csv()
    parsed = rows(text)
    assert list(parsed[0].keys()) == data.COLUMNS
    assert len(parsed) == data.MONTHS * len(data.REGIONS) * len(data.PRODUCTS)


def test_same_seed_gives_same_data():
    assert data.make_sales_csv(seed=3) == data.make_sales_csv(seed=3)
    assert data.make_sales_csv(seed=3) != data.make_sales_csv(seed=4)


def test_revenue_is_units_times_price():
    for row in rows(data.make_sales_csv()):
        assert round(int(row["units"]) * float(row["unit_price"]), 2) == float(row["revenue"])


def test_months_are_iso_and_in_order():
    months = sorted({row["month"] for row in rows(data.make_sales_csv())})
    assert months[0] == "2025-01"
    assert months[-1] == "2025-12"
