"""Step 5: run SQL queries safely on olist.db."""

import re
import sqlite3

import pandas as pd

from schema import DB_PATH

MAX_ROWS = 1000  # never return more rows than this

# Commands that change or damage the database.
FORBIDDEN_WORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
    "REPLACE INTO", "ATTACH", "DETACH", "PRAGMA", "VACUUM", "REINDEX",
]


def check_sql_is_safe(sql):
    """Return the cleaned SQL, or raise ValueError if it is not one read-only query."""
    cleaned = re.sub(r"--.*", "", sql)          # remove SQL comments
    cleaned = cleaned.strip().rstrip(";").strip()

    if not cleaned:
        raise ValueError("The query is empty.")

    if ";" in cleaned:
        raise ValueError("Only one query is allowed.")

    first_word = cleaned.split()[0].upper()
    if first_word not in ("SELECT", "WITH"):
        raise ValueError("Only SELECT queries are allowed.")

    for word in FORBIDDEN_WORDS:
        if re.search(rf"\b{word}\b", cleaned, re.IGNORECASE):
            raise ValueError(f"The query contains a forbidden command: {word}")

    return cleaned


def run_query(sql):
    """Check the SQL, run it on the database and return the result as a DataFrame."""
    sql = check_sql_is_safe(sql)

    # mode=ro opens the database READ-ONLY: even if a bad query got past
    # the check above, SQLite itself refuses to change any data.
    conn = sqlite3.connect(DB_PATH.as_uri() + "?mode=ro", uri=True)
    try:
        cursor = conn.execute(sql)
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchmany(MAX_ROWS)
    finally:
        conn.close()

    return pd.DataFrame(rows, columns=columns)


if __name__ == "__main__":
    tests = [
        "SELECT COUNT(*) AS total_orders FROM orders;",
        "DELETE FROM orders",
        "DROP TABLE customers",
        "SELECT * FROM orders; DROP TABLE orders",
        "SELECT YEAR(purchase_date) AS year FROM orders",
    ]

    for sql in tests:
        print("=" * 60)
        print("SQL:", sql)
        try:
            print("OK:\n" + run_query(sql).to_string(index=False))
        except ValueError as error:
            print("BLOCKED:", error)
        except sqlite3.Error as error:
            print("SQL ERROR:", error)