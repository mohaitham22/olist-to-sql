"""Step 8: measure how often the AI answers correctly.

For every test question we have a correct "reference" SQL query written by hand.
We run the AI's SQL and the reference SQL and compare the results.
"""

import sqlite3
import time

from db import run_query
from llm import ask_database

# (question, correct SQL)
TESTS = [
    # --- Easy: one table ---
    ("How many orders are there in total?",
     "SELECT COUNT(*) FROM orders"),
    ("How many sellers are there?",
     "SELECT COUNT(*) FROM sellers"),
    ("How many orders were canceled?",
     "SELECT COUNT(*) FROM orders WHERE order_status = 'canceled'"),
    ("What is the average review score?",
     "SELECT AVG(review_score) FROM reviews"),
    ("How many orders were paid with a bank slip?",
     "SELECT COUNT(DISTINCT order_id) FROM payments WHERE payment_type = 'bank_slip'"),
    ("What is the most common number of payment installments?",
     "SELECT payment_installments FROM payments GROUP BY payment_installments ORDER BY COUNT(*) DESC LIMIT 1"),
    ("Which 5 states have the most sellers?",
     "SELECT seller_state, COUNT(*) FROM sellers GROUP BY seller_state ORDER BY COUNT(*) DESC LIMIT 5"),

    # --- Dates ---
    ("How many orders were made in 2017?",
     "SELECT COUNT(*) FROM orders WHERE strftime('%Y', purchase_date) = '2017'"),
    ("Which month in 2018 had the most orders?",
     "SELECT strftime('%Y-%m', purchase_date) FROM orders WHERE strftime('%Y', purchase_date) = '2018' "
     "GROUP BY 1 ORDER BY COUNT(*) DESC LIMIT 1"),
    ("What is the average delivery time in days?",
     "SELECT AVG(julianday(delivered_date) - julianday(purchase_date)) FROM orders"),
    ("How many orders were delivered late?",
     "SELECT COUNT(*) FROM orders WHERE delivered_date > estimated_delivery_date"),

    # --- JOINs ---
    ("What are the top 5 product categories by revenue?",
     "SELECT p.product_category, SUM(oi.price) FROM order_items oi "
     "JOIN products p ON p.product_id = oi.product_id GROUP BY 1 ORDER BY 2 DESC LIMIT 5"),
    ("Which 5 customer states have the most unique customers?",
     "SELECT customer_state, COUNT(DISTINCT customer_unique_id) FROM customers GROUP BY 1 ORDER BY 2 DESC LIMIT 5"),
    ("Which 3 cities have the most sellers?",
     "SELECT seller_city, COUNT(*) FROM sellers GROUP BY 1 ORDER BY 2 DESC LIMIT 3"),
    ("How many orders contain products from the electronics category?",
     "SELECT COUNT(DISTINCT oi.order_id) FROM order_items oi "
     "JOIN products p ON p.product_id = oi.product_id WHERE p.product_category = 'electronics'"),
    ("Which 5 sellers have sold the most items?",
     "SELECT seller_id, COUNT(*) FROM order_items GROUP BY 1 ORDER BY 2 DESC LIMIT 5"),
    ("What is the total shipping cost paid by customers in SP?",
     "SELECT SUM(oi.freight_value) FROM order_items oi JOIN orders o ON o.order_id = oi.order_id "
     "JOIN customers c ON c.customer_id = o.customer_id WHERE c.customer_state = 'SP'"),
    ("What was the total revenue in 2018?",
     "SELECT SUM(oi.price) FROM order_items oi JOIN orders o ON o.order_id = oi.order_id "
     "WHERE strftime('%Y', o.purchase_date) = '2018'"),
    ("Which payment type has the highest average number of installments?",
     "SELECT payment_type FROM payments GROUP BY 1 ORDER BY AVG(payment_installments) DESC LIMIT 1"),
    ("Which customer state has the longest average delivery time?",
     "SELECT c.customer_state FROM orders o JOIN customers c ON c.customer_id = o.customer_id "
     "WHERE o.delivered_date IS NOT NULL GROUP BY 1 "
     "ORDER BY AVG(julianday(o.delivered_date) - julianday(o.purchase_date)) DESC LIMIT 1"),
]


def normalize(column):
    """Make values comparable: round numbers to 1 decimal, lowercase text, sort."""
    values = []
    for value in column:
        try:
            values.append(str(round(float(value), 1)))
        except (TypeError, ValueError):
            values.append(str(value).strip().lower())
    return sorted(values)


def results_match(expected, actual):
    """Pass if every column of the correct result also appears in the AI's result.

    Column names and extra columns do not matter, only the values.
    """
    actual_columns = [normalize(actual[col]) for col in actual.columns]
    return all(normalize(expected[col]) in actual_columns for col in expected.columns)


def main():
    passed = 0
    start = time.time()

    for number, (question, correct_sql) in enumerate(TESTS, start=1):
        expected = run_query(correct_sql)
        try:
            sql, actual = ask_database(question)
            ok = results_match(expected, actual)
        except (ValueError, sqlite3.Error) as error:
            sql, ok = f"ERROR: {error}", False

        passed += ok
        print(f"{'PASS' if ok else 'FAIL'}  {number:2}. {question}")
        if not ok:
            print("      AI SQL:\n      " + sql.replace("\n", "\n      "))
            print("      Expected:", expected.to_dict("records")[:5])

    accuracy = 100 * passed / len(TESTS)
    print(f"\nAccuracy: {passed}/{len(TESTS)} = {accuracy:.0f}%  ({time.time() - start:.0f} seconds)")


if __name__ == "__main__":
    main()