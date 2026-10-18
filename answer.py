"""Step 6: turn the query result into a clear answer in plain English."""

import sqlite3

import ollama

from llm import MODEL, ask_database

MAX_ROWS_FOR_AI = 20  # the AI only needs the top rows to write the answer

# Rules for the AI on HOW to explain the result.
ANSWER_INSTRUCTIONS = """You are a helpful data analyst. You explain database results to a business manager.

Follow these rules:
- Answer the question directly in 1 to 3 short sentences.
- Use ONLY the numbers in the result. Never invent or estimate numbers.
- Write money in Brazilian Real like R$ 1,234.56 and big numbers with commas like 45,101.
- If the result is a list, mention the top items (at most 5).
- If the result is empty, say that no data was found for this question.
- Do not mention SQL, tables, columns or queries. Write in simple English."""


def result_to_text(result):
    """Turn the result table into text the AI can read."""
    if result.empty:
        return "The result is empty (0 rows)."

    text = result.head(MAX_ROWS_FOR_AI).to_string(index=False)
    if len(result) > MAX_ROWS_FOR_AI:
        text += f"\n... showing the first {MAX_ROWS_FOR_AI} of {len(result)} rows"
    return text


def generate_answer(question, sql, result):
    """Ask the model to explain the result in plain English."""
    messages = [
        {"role": "system", "content": ANSWER_INSTRUCTIONS},
        {
            "role": "user",
            "content": f"Question: {question}\n\n"
                       f"SQL that was used:\n{sql}\n\n"
                       f"Result:\n{result_to_text(result)}",
        },
    ]
    response = ollama.chat(model=MODEL, messages=messages, options={"temperature": 0})
    return response["message"]["content"].strip()


if __name__ == "__main__":
    test_questions = [
        "What are the top 5 product categories by revenue?",
        "What is the average review score for late deliveries vs on-time deliveries?",
        "How many unique customers do we have in each of the top 3 states?",
        "List the orders delivered in 2015",
    ]

    for question in test_questions:
        print("=" * 70)
        print("QUESTION:", question)
        try:
            sql, result = ask_database(question)
        except ValueError as error:
            print("BLOCKED:", error)
            continue
        except sqlite3.Error as error:
            print("FAILED:", error)
            continue

        print("SQL:\n" + sql)
        print("RESULT:\n" + result_to_text(result))
        print("ANSWER:", generate_answer(question, sql, result))