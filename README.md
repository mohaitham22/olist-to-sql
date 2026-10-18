# 🛒 Olist SQL Assistant: ask your data questions in plain English

A local AI app that turns business questions into SQL, runs them on a SQLite database,
and explains the results in plain English. It runs 100% on your own computer:
no API keys, no cost, and the data never leaves your machine.

![App screenshot](images/app.png)

## ✨ Features
- **Plain English → SQL**: ask *"Which month in 2017 had the most orders?"* and get the SQL query
- **Clear answers**: the result is explained in 1–3 sentences, with the SQL and the result table
- **Automatic charts**: bar charts for categories, line charts for dates
- **Auto-fix**: if a query fails, the AI reads the error and corrects its own SQL
- **Safe**: only read-only `SELECT` queries can run (2 layers of protection)
- **Tested**: 20/20 correct on a hand-written test set

## 🧠 How it works
```
question ─► llm.py ─► SQL ─► db.py ─► result table ─► answer.py ─► plain-English answer
              ▲                │
              └── auto-fix ◄───┘ (if the SQL fails)
```
1. **`schema.py`** describes every table, column, relationship and business rule for the AI
2. **`llm.py`** builds a prompt (schema + rules + 3 examples) and asks the model for SQL
3. **`db.py`** checks that the SQL is safe and runs it on a **read-only** connection
4. **`answer.py`** sends the result back to the model to explain it in plain English
5. **`app.py`** is the Streamlit interface

## 🛠️ Tech stack
| Tool | Use |
|---|---|
| Python 3.12 | main language |
| Ollama + `qwen2.5-coder:7b` | local AI model for SQL and answers |
| SQLite | database (7 tables, ~550k rows) |
| pandas | data cleaning and loading |
| Streamlit | web interface |

## 📊 Dataset
[Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce):
about 100k real, anonymized orders from 2016–2018.

Data preparation (`load_data.py`):
- 7 tables: `customers`, `sellers`, `orders`, `order_items`, `payments`, `reviews`, `products`
- renamed long columns to clear names (e.g. `order_delivered_customer_date` → `delivered_date`)
- translated product categories and payment types from Portuguese to English
- kept real missing values as NULL (e.g. a missing `delivered_date` = not delivered)
- added indexes on all ID columns for fast JOINs

## 🔒 Safety
The AI writes SQL, so its output is never trusted:
1. `check_sql_is_safe()` allows only one `SELECT` / `WITH` query and blocks words like `DELETE` and `DROP`
2. the database is opened in **read-only mode**, so SQLite itself refuses any change
3. results are limited to 1,000 rows

## ✅ Evaluation
`evaluate.py` runs 20 test questions (easy, dates, JOINs). For each one it compares the
result of the AI's SQL with the result of a hand-written correct query (*execution accuracy*).

**Result: 20/20 (100%)**

## 🚀 How to run
1. Install [Ollama](https://ollama.com/download) and download the model:
   ```
   ollama pull qwen2.5-coder:7b
   ```
2. Download the [dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) and put the CSV files in `data/`
3. Create the environment and install the libraries:
   ```
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```
4. Build the database and start the app:
   ```
   python load_data.py
   streamlit run app.py
   ```

## 💡 Example questions
- What are the top 5 product categories by revenue?
- What is the average review score for late deliveries vs on-time deliveries?
- Which 10 cities have the most unique customers?
- What is the average delivery time in days for each customer state?

## ⚠️ Limitations
- Each answer takes about 15–25 seconds on a laptop (the model runs twice)
- Review comments are in Portuguese
- A 7B model can still make mistakes on very complex or unclear questions, so the SQL is always shown for checking