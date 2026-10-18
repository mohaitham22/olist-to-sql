"""Step 2: load the Olist CSV files into one SQLite database (olist.db)."""

import sqlite3
from pathlib import Path

import pandas as pd

PROJECT_DIR = Path(__file__).parent
DATA_DIR = PROJECT_DIR / "data"
DB_PATH = PROJECT_DIR / "olist.db"


def read_csv(name):
    return pd.read_csv(DATA_DIR / name)


def load_customers():
    df = read_csv("olist_customers_dataset.csv")
    return df.rename(columns={"customer_zip_code_prefix": "customer_zip_code"})


def load_sellers():
    df = read_csv("olist_sellers_dataset.csv")
    return df.rename(columns={"seller_zip_code_prefix": "seller_zip_code"})


def load_orders():
    df = read_csv("olist_orders_dataset.csv")
    # Shorter, clearer names make it easier for the AI to write correct SQL.
    return df.rename(columns={
        "order_purchase_timestamp": "purchase_date",
        "order_approved_at": "approved_date",
        "order_delivered_carrier_date": "shipped_date",
        "order_delivered_customer_date": "delivered_date",
        "order_estimated_delivery_date": "estimated_delivery_date",
    })


def load_order_items():
    df = read_csv("olist_order_items_dataset.csv")
    return df.rename(columns={"order_item_id": "item_number"})


def load_payments():
    df = read_csv("olist_order_payments_dataset.csv")
    # "boleto" is Portuguese: a Brazilian bank payment slip.
    df["payment_type"] = df["payment_type"].replace({"boleto": "bank_slip"})
    return df


def load_reviews():
    df = read_csv("olist_order_reviews_dataset.csv")
    return df.rename(columns={
        "review_creation_date": "review_date",
        "review_answer_timestamp": "review_answer_date",
    })


# Categories missing from the translation file, plus spelling mistakes in it.
CATEGORY_FIXES = {
    "pc_gamer": "gaming_pc",
    "portateis_cozinha_e_preparadores_de_alimentos": "portable_kitchen_food_preparers",
    "la_cuisine": "kitchen",
    "costruction_tools_garden": "construction_tools_garden",
    "costruction_tools_tools": "construction_tools_tools",
    "fashio_female_clothing": "fashion_female_clothing",
    "home_confort": "home_comfort",
    "arts_and_craftmanship": "arts_and_craftsmanship",
}


def load_products():
    df = read_csv("olist_products_dataset.csv")
    translation = read_csv("product_category_name_translation.csv")

    # Replace the Portuguese category name with the English one.
    df = df.merge(translation, on="product_category_name", how="left")
    # Products with no category get "unknown".
    df["product_category"] = (
        df["product_category_name_english"]
        .fillna(df["product_category_name"])
        .fillna("unknown")
        .replace(CATEGORY_FIXES)
    )

    # Keep only the useful columns (name/description lengths are not useful).
    return df[[
        "product_id",
        "product_category",
        "product_photos_qty",
        "product_weight_g",
        "product_length_cm",
        "product_height_cm",
        "product_width_cm",
    ]]


TABLES = {
    "customers": load_customers,
    "sellers": load_sellers,
    "orders": load_orders,
    "order_items": load_order_items,
    "payments": load_payments,
    "reviews": load_reviews,
    "products": load_products,
}

# Indexes on the ID columns make JOINs fast.
INDEXES = [
    ("customers", "customer_id"),
    ("customers", "customer_unique_id"),
    ("sellers", "seller_id"),
    ("orders", "order_id"),
    ("orders", "customer_id"),
    ("order_items", "order_id"),
    ("order_items", "product_id"),
    ("order_items", "seller_id"),
    ("payments", "order_id"),
    ("reviews", "order_id"),
    ("products", "product_id"),
]


def main():
    # Start fresh every time the script runs.
    if DB_PATH.exists():
        DB_PATH.unlink()

    with sqlite3.connect(DB_PATH) as conn:
        for table_name, load in TABLES.items():
            df = load()
            df.to_sql(table_name, conn, index=False)
            print(f"{table_name:12} {len(df):>7,} rows  {len(df.columns)} columns")

        for table_name, column in INDEXES:
            conn.execute(
                f"CREATE INDEX idx_{table_name}_{column} ON {table_name} ({column})"
            )

    print(f"\nDatabase saved to {DB_PATH.name}")


if __name__ == "__main__":
    main()
