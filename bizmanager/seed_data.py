#!/usr/bin/env python3
"""Load sample products and customers for testing."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from database import db

SAMPLE_PRODUCTS = [
    {"name": "Tomato", "category": "Vegetables", "unit": "kg", "cost_price": 28, "selling_price": 40, "stock_quantity": 60, "min_stock_level": 10},
    {"name": "Potato", "category": "Vegetables", "unit": "kg", "cost_price": 22, "selling_price": 32, "stock_quantity": 100, "min_stock_level": 20},
    {"name": "Red Onion", "category": "Vegetables", "unit": "kg", "cost_price": 30, "selling_price": 45, "stock_quantity": 75, "min_stock_level": 15},
    {"name": "Spinach", "category": "Leafy Greens", "unit": "bunch", "cost_price": 10, "selling_price": 15, "stock_quantity": 25, "min_stock_level": 8},
    {"name": "Coriander", "category": "Herbs", "unit": "bunch", "cost_price": 6, "selling_price": 10, "stock_quantity": 30, "min_stock_level": 10},
    {"name": "Carrot", "category": "Vegetables", "unit": "kg", "cost_price": 36, "selling_price": 52, "stock_quantity": 40, "min_stock_level": 10},
]

SAMPLE_CUSTOMERS = [
    {
        "name": "John Smith",
        "address": "123 Main St, Springfield",
        "gst": "29ABCDE1234F1Z5",
    },
    {
        "name": "Sarah Johnson",
        "address": "456 Oak Ave, Riverside",
        "gst": "29FGHIJ5678K2Z6",
    },
]


def seed():
    db.init_db()
    categories = {c["name"]: c["id"] for c in db.get_categories()}

    for p in SAMPLE_PRODUCTS:
        cat_id = categories.get(p.pop("category"))
        p["category_id"] = cat_id
        try:
            db.add_product(p)
            print(f"  Added product: {p['name']}")
        except Exception as e:
            print(f"  Skipped {p['name']}: {e}")

    for c in SAMPLE_CUSTOMERS:
        try:
            db.add_customer(c)
            print(f"  Added customer: {c['name']}")
        except Exception as e:
            print(f"  Skipped {c['name']}: {e}")

    print("\nSample data loaded successfully!")


if __name__ == "__main__":
    print("Seeding sample data...\n")
    seed()
