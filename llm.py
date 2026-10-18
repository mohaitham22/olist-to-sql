"""Steps 4-5: turn a question into SQL, run it safely, and auto-fix errors."""

import re
import sqlite3

import ollama

from db import run_query
from schema import get_schema_text

MODEL = "qwen2.5-coder:7b"
MAX_FIX_ATTEMPTS = 2  # how many times the model may try to fix a failed query

# Rules for the AI on HOW to write the SQL.
INSTRUCTIONS = """You are an expert data analyst. You write SQLite queries for the database described above.

Follow these rules:
- Write ONE SQLite query that answers the question.
- Only write SELECT queries. Never use INSERT, UPDATE, DELETE, DROP or ALTER.
- Use only the tables and columns listed above.
- Use SQLite functions only: strftime() and julianday() for dates. Never use YEAR(), MONTH() or DATEDIFF().
- Give every calculated column a clear name with AS, e.g. AS total_revenue.
- Round money and averages to 2 decimals with ROUND(x, 2).
- If the question asks for a list, add LIMIT (use the number in the question, otherwise LIMIT 20).
- Return only the SQL inside a ```sql block. No explanation."""

# A few example questions with correct answers. The AI copies their style.
EXAMPLES = [
    (
        "What are the top 5 product categories by revenue?",
        """SELECT p.product_category, ROUND(SUM(oi.price), 2) AS total_revenue
FROM order_items oi
JOIN products p ON p.product_id = oi.product_id
GROUP BY p.product_category
ORDER BY total_revenue DESC
LIMIT 5;""",
    ),
    (
        "How many orders were delivered late in 2018?",
        """SELECT COUNT(*) AS late_orders
FROM orders
WHERE delivered_date > estimated_delivery_date
  AND strftime('%Y', purchase_date) = '2018';""",
    ),
    (
        "What is the average delivery time in days for each customer state?",
        """SELECT c.customer_state,
       ROUND(AVG(julianday(o.delivered_date) - julianday(o.purchase_date)), 2) AS avg_delivery_days
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
WHERE o.delivered_date IS NOT NULL
GROUP BY c.customer_state
ORDER BY avg_delivery_days DESC
LIMIT 20;""",
    ),
]


def build_messages(question):
    """Build the chat messages: schema + rules, then the examples, then the question."""
    messages = [{"role": "system", "content": get_schema_text() + "\n\n" + INSTRUCTIONS}]

    for example_question, example_sql in EXAMPLES:
        messages.append({"role": "user", "content": example_question})
        messages.append({"role": "assistant", "content": f"```sql\n{example_sql}\n```"})

    messages.append({"role": "user", "content": question})
    return messages


def extract_sql(text):
    """Take the SQL out of the model's reply (remove the ```sql ... ``` marks)."""
    match = re.search(r"```(?:sql)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    sql = match.group(1) if match else text
    return sql.strip()


def generate_sql(question):
    """Send the question to the model and return the SQL query."""
    response = ollama.chat(
        model=MODEL,
        messages=build_messages(question),
        options={"temperature": 0},  # 0 = same question gives the same answer
    )
    return extract_sql(response["message"]["content"])


def fix_sql(question, bad_sql, error):
    """Show the model its failed query and the error, and ask for a corrected query."""
    messages = build_messages(question)
    messages.append({"role": "assistant", "content": f"```sql\n{bad_sql}\n```"})
    messages.append({
        "role": "user",
        "content": f"This query failed with this error:\n{error}\n\n"
                   "Read the TABLES list again: use only columns that exist in each table, "
                   "and JOIN tables only as shown in RELATIONSHIPS. "
                   "Write a corrected query that is DIFFERENT from the failed one. "
                   "Return only the corrected SQL inside a ```sql block.",
    })
    response = ollama.chat(model=MODEL, messages=messages, options={"temperature": 0})
    return extract_sql(response["message"]["content"])


def ask_database(question):
    """Question -> SQL -> result table. If the SQL fails, let the model fix it.

    Returns (sql, dataframe). Raises ValueError for unsafe SQL (it is never "fixed")
    and sqlite3.Error if the query still fails after all fix attempts.
    """
    sql = generate_sql(question)

    for attempt in range(MAX_FIX_ATTEMPTS + 1):
        try:
            return sql, run_query(sql)
        except sqlite3.Error as error:
            if attempt == MAX_FIX_ATTEMPTS:
                raise
            print(f"  Attempt {attempt + 1} failed: {error} -> asking the model to fix it")
            sql = fix_sql(question, sql, error)


if __name__ == "__main__":
    # 1) Auto-fix demo: give the model a broken query on purpose.
    print("=" * 70)
    print("AUTO-FIX DEMO")
    question = "How many orders were made each year?"
    bad_sql = "SELECT YEAR(purchase_date) AS year, COUNT(*) AS total_orders FROM orders GROUP BY year"
    try:
        run_query(bad_sql)
    except sqlite3.Error as error:
        print("Broken SQL:", bad_sql)
        print("Error:", error)
        fixed_sql = fix_sql(question, bad_sql, error)
        print("Fixed SQL:\n" + fixed_sql)
        print("RESULT:\n" + run_query(fixed_sql).to_string(index=False))

    # 2) Full flow: question -> SQL -> safe run (with auto-fix if needed).
    test_questions = [
        "What are the 5 most used payment types and how much was paid with each?",
        "Which month in 2017 had the most orders?",
        "Delete all canceled orders",
    ]

    for question in test_questions:
        print("=" * 70)
        print("QUESTION:", question)
        try:
            sql, result = ask_database(question)
            print("SQL:\n" + sql)
            print("RESULT:\n" + result.to_string(index=False))
        except ValueError as error:
            print("BLOCKED:", error)
        except sqlite3.Error as error:
            print("FAILED after all fix attempts:", error)