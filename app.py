"""Step 7: the Streamlit app. Ask questions about the Olist data in plain English."""

import re
import sqlite3
import time

import pandas as pd
import streamlit as st

from answer import generate_answer
from llm import ask_database
from schema import TABLES

EXAMPLE_QUESTIONS = [
    "What are the top 5 product categories by revenue?",
    "Which month in 2017 had the most orders?",
    "What is the average review score for late deliveries vs on-time deliveries?",
    "Which 10 cities have the most unique customers?",
    "How much money was paid with each payment type?",
    "What is the average delivery time in days for each customer state?",
]

st.set_page_config(page_title="Olist SQL Assistant", page_icon="🛒", layout="wide")


def handle_question(question):
    """Run the full pipeline: question -> SQL -> result -> answer."""
    response = {"question": question}
    start = time.time()
    try:
        with st.spinner("🧠 Writing the SQL query..."):
            sql, result = ask_database(question)
        with st.spinner("✍️ Writing the answer..."):
            answer = generate_answer(question, sql, result)
        response.update(sql=sql, result=result, answer=answer)
    except ValueError as error:
        response["error"] = f"🛑 Blocked: {error} This app can only read data, not change it."
    except sqlite3.Error as error:
        response["error"] = f"⚠️ The AI could not write a working query ({error}). Try asking in a different way."
    except Exception as error:  # for example: Ollama is not running
        response["error"] = f"❌ Could not reach the AI model. Is Ollama running? ({error})"
    response["seconds"] = time.time() - start
    return response


def show_chart(result):
    """Draw a chart when the result is one label column + one number column."""
    if len(result.columns) != 2 or not 2 <= len(result) <= 30:
        return
    label, value = result.columns
    if not pd.api.types.is_numeric_dtype(result[value]):
        return

    # Labels like 2017, 2017-11 or 2017-11-24 are dates -> line chart over time.
    if re.fullmatch(r"\d{4}(-\d{2}){0,2}", str(result[label].iloc[0])):
        st.line_chart(result, x=label, y=value)
    else:
        st.bar_chart(result, x=label, y=value, horizontal=True, sort=False)


def show_response(response):
    """Show one answer: the answer text, the SQL, the result table and a chart."""
    if "error" in response:
        st.error(response["error"])
        return

    st.success(response["answer"], icon="💬")
    st.caption(f"⏱️ {response['seconds']:.1f} seconds")

    sql_col, table_col = st.columns(2)
    with sql_col:
        st.markdown("**🧾 SQL query**")
        st.code(response["sql"], language="sql")
    with table_col:
        st.markdown(f"**📋 Result ({len(response['result'])} rows)**")
        st.dataframe(response["result"], hide_index=True)

    show_chart(response["result"])


# ---------- Sidebar: example questions + database tables ----------
if "history" not in st.session_state:
    st.session_state.history = []

clicked_example = None
with st.sidebar:
    st.header("💡 Example questions")
    for example in EXAMPLE_QUESTIONS:
        if st.button(example, width="stretch"):
            clicked_example = example

    st.header("🗂️ Database tables")
    for table, columns in TABLES.items():
        with st.expander(table):
            for column, description in columns.items():
                st.markdown(f"- **{column}**: {description}")

    if st.button("🗑️ Clear history", width="stretch"):
        st.session_state.history = []

# ---------- Main page ----------
st.title("🛒 Olist SQL Assistant")
st.caption(
    "Ask a question about the Olist Brazilian e-commerce data (2016–2018) in plain English. "
    "A local AI model writes the SQL, runs it on SQLite, and explains the result."
)

# Show the previous questions and answers.
for item in st.session_state.history:
    with st.chat_message("user"):
        st.markdown(item["question"])
    with st.chat_message("assistant"):
        show_response(item)

# A new question comes from the chat box or from an example button.
question = st.chat_input("Ask a question, e.g. Which state has the most customers?")
question = question or clicked_example

if question:
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        response = handle_question(question)
        show_response(response)
    st.session_state.history.append(response)