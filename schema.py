"""Step 3: describe the database so the AI can write correct SQL."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "olist.db"

# Every table and column, with a short description for the AI.
TABLES = {
    "customers": {
        "customer_id": "ID of the customer for ONE order (a new ID for every order)",
        "customer_unique_id": "real ID of the person (use it to count unique customers)",
        "customer_zip_code": "zip code prefix",
        "customer_city": "city name in lowercase, e.g. 'sao paulo'",
        "customer_state": "2-letter Brazilian state code, e.g. 'SP', 'RJ', 'MG'",
    },
    "sellers": {
        "seller_id": "ID of the seller",
        "seller_zip_code": "zip code prefix",
        "seller_city": "city name in lowercase",
        "seller_state": "2-letter Brazilian state code",
    },
    "orders": {
        "order_id": "ID of the order",
        "customer_id": "links to customers.customer_id",
        "order_status": "delivered, shipped, canceled, unavailable, invoiced, processing, created, approved",
        "purchase_date": "when the customer bought",
        "approved_date": "when the payment was approved (NULL if never approved)",
        "shipped_date": "when it was given to the shipping company (NULL if not shipped)",
        "delivered_date": "when the customer received it (NULL if not delivered)",
        "estimated_delivery_date": "the delivery date promised to the customer",
    },
    "order_items": {
        "order_id": "links to orders.order_id",
        "item_number": "1, 2, 3... for each item in the same order",
        "product_id": "links to products.product_id",
        "seller_id": "links to sellers.seller_id",
        "shipping_limit_date": "last date for the seller to ship the item",
        "price": "price of this item in BRL (R$)",
        "freight_value": "shipping cost of this item in BRL (R$)",
    },
    "payments": {
        "order_id": "links to orders.order_id",
        "payment_sequential": "1, 2, 3... if the order was paid with more than one method",
        "payment_type": "credit_card, bank_slip, voucher, debit_card, not_defined",
        "payment_installments": "number of monthly installments",
        "payment_value": "amount paid in BRL (R$)",
    },
    "reviews": {
        "review_id": "ID of the review",
        "order_id": "links to orders.order_id",
        "review_score": "customer rating from 1 (worst) to 5 (best)",
        "review_comment_title": "title of the comment, in PORTUGUESE (often NULL)",
        "review_comment_message": "comment text, in PORTUGUESE (often NULL)",
        "review_date": "when the review was sent to the customer",
        "review_answer_date": "when the customer answered the review",
    },
    "products": {
        "product_id": "ID of the product",
        "product_category": "English category in lowercase with underscores, e.g. 'health_beauty', 'bed_bath_table', 'electronics' ('unknown' if missing)",
        "product_photos_qty": "number of photos in the listing",
        "product_weight_g": "weight in grams",
        "product_length_cm": "length in cm",
        "product_height_cm": "height in cm",
        "product_width_cm": "width in cm",
    },
}

# How the tables connect (used for JOINs).
RELATIONSHIPS = [
    "orders.customer_id = customers.customer_id",
    "order_items.order_id = orders.order_id",
    "order_items.product_id = products.product_id",
    "order_items.seller_id = sellers.seller_id",
    "payments.order_id = orders.order_id",
    "reviews.order_id = orders.order_id",
]

# Business rules the AI cannot guess from column names.
RULES = [
    "Data covers orders from 2016-09-04 to 2018-10-17. Money is in Brazilian Real (BRL, R$).",
    "Dates are TEXT like '2017-10-02 10:56:33'. Use strftime('%Y', col) for year, strftime('%Y-%m', col) for month.",
    "Days between two dates: julianday(date2) - julianday(date1).",
    "Revenue / sales = SUM(order_items.price). Shipping cost = SUM(order_items.freight_value).",
    "Total amount paid by customers = SUM(payments.payment_value).",
    "Never join order_items and payments in the same query with SUM: it counts money twice.",
    "Count unique customers with COUNT(DISTINCT customers.customer_unique_id), not customer_id.",
    "A late delivery means delivered_date > estimated_delivery_date.",
    "Delivery time in days = julianday(delivered_date) - julianday(purchase_date).",
    "One order can have many items, many payments, and (rarely) more than one review.",
    "The orders table has NO seller_id and NO product_id. To reach sellers or products from orders, JOIN order_items.",
    "Customer location = customers.customer_state / customer_city. Seller location = sellers.seller_state / seller_city. A question about customers uses the customer columns.",
]


def get_schema_text():
    """Build the full schema description as one text for the AI prompt."""
    lines = ["TABLES:"]
    for table, columns in TABLES.items():
        lines.append(f"\nTable {table}:")
        for column, description in columns.items():
            lines.append(f"  - {column}: {description}")

    lines.append("\nRELATIONSHIPS (for JOINs):")
    for relationship in RELATIONSHIPS:
        lines.append(f"  - {relationship}")

    lines.append("\nRULES:")
    for rule in RULES:
        lines.append(f"  - {rule}")

    return "\n".join(lines)


def check_schema():
    """Make sure every table and column above really exists in olist.db."""
    conn = sqlite3.connect(DB_PATH)
    all_ok = True

    for table, columns in TABLES.items():
        # PRAGMA table_info returns one row per column; row[1] is the column name.
        real_columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}

        if not real_columns:
            print(f"ERROR: table '{table}' does not exist in the database")
            all_ok = False
            continue

        for column in columns:
            if column not in real_columns:
                print(f"ERROR: column '{table}.{column}' does not exist")
                all_ok = False

        for column in real_columns - set(columns):
            print(f"WARNING: column '{table}.{column}' is in the database but not described")

    conn.close()
    return all_ok


if __name__ == "__main__":
    print(get_schema_text())
    print("\n" + "=" * 60)
    if check_schema():
        print("Schema check passed: every table and column exists in olist.db")