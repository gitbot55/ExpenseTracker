from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime

app = Flask(__name__)


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


# =========================================================
# CREATE TABLE
# =========================================================

def create_table():

    conn = get_db_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            type TEXT NOT NULL,
            date TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


create_table()


# =========================================================
# DATE FORMATTER
# =========================================================

@app.template_filter("format_date")
def format_date(value):

    if not value:
        return ""

    try:

        date_object = datetime.strptime(
            value,
            "%Y-%m-%d"
        )

        return date_object.strftime(
            "%d %b %Y"
        )

    except (ValueError, TypeError):

        return value


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/")
def index():

    conn = get_db_connection()


    # -----------------------------------------------------
    # TOTAL INCOME
    # -----------------------------------------------------

    income = conn.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE type = 'Income'
    """).fetchone()[0]


    # -----------------------------------------------------
    # TOTAL EXPENSE
    # -----------------------------------------------------

    expense = conn.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE type = 'Expense'
    """).fetchone()[0]


    # -----------------------------------------------------
    # BALANCE
    # -----------------------------------------------------

    balance = income - expense


    # -----------------------------------------------------
    # TOTAL TRANSACTIONS
    # -----------------------------------------------------

    total_transactions = conn.execute("""
        SELECT COUNT(*)
        FROM transactions
    """).fetchone()[0]


    # -----------------------------------------------------
    # INCOME TRANSACTION COUNT
    # -----------------------------------------------------

    income_count = conn.execute("""
        SELECT COUNT(*)
        FROM transactions
        WHERE type = 'Income'
    """).fetchone()[0]


    # -----------------------------------------------------
    # EXPENSE TRANSACTION COUNT
    # -----------------------------------------------------

    expense_count = conn.execute("""
        SELECT COUNT(*)
        FROM transactions
        WHERE type = 'Expense'
    """).fetchone()[0]


    # -----------------------------------------------------
    # AVERAGE EXPENSE
    # -----------------------------------------------------

    average_expense = conn.execute("""
        SELECT COALESCE(AVG(amount), 0)
        FROM transactions
        WHERE type = 'Expense'
    """).fetchone()[0]


    # -----------------------------------------------------
    # AVERAGE INCOME
    # -----------------------------------------------------

    average_income = conn.execute("""
        SELECT COALESCE(AVG(amount), 0)
        FROM transactions
        WHERE type = 'Income'
    """).fetchone()[0]


    # -----------------------------------------------------
    # LARGEST EXPENSE
    # -----------------------------------------------------

    largest_expense = conn.execute("""
        SELECT COALESCE(MAX(amount), 0)
        FROM transactions
        WHERE type = 'Expense'
    """).fetchone()[0]


    # -----------------------------------------------------
    # LARGEST INCOME
    # -----------------------------------------------------

    largest_income = conn.execute("""
        SELECT COALESCE(MAX(amount), 0)
        FROM transactions
        WHERE type = 'Income'
    """).fetchone()[0]


    # -----------------------------------------------------
    # RECENT TRANSACTIONS
    # -----------------------------------------------------

    transactions = conn.execute("""
        SELECT *
        FROM transactions
        ORDER BY date DESC, id DESC
        LIMIT 10
    """).fetchall()


    # -----------------------------------------------------
    # EXPENSE BY CATEGORY
    # -----------------------------------------------------

    category_data = conn.execute("""
        SELECT
            category,
            SUM(amount) AS total
        FROM transactions
        WHERE type = 'Expense'
        GROUP BY category
        ORDER BY total DESC
    """).fetchall()


    # -----------------------------------------------------
    # INCOME VS EXPENSE
    # -----------------------------------------------------

    income_expense_data = [
        {
            "type": "Income",
            "total": income
        },
        {
            "type": "Expense",
            "total": expense
        }
    ]


    conn.close()


    return render_template(
        "index.html",

        income=income,

        expense=expense,

        balance=balance,

        total_transactions=total_transactions,

        income_count=income_count,

        expense_count=expense_count,

        average_expense=average_expense,

        average_income=average_income,

        largest_expense=largest_expense,

        largest_income=largest_income,

        transactions=transactions,

        category_data=category_data,

        income_expense_data=income_expense_data
    )


# =========================================================
# ADD TRANSACTION
# =========================================================

@app.route("/add", methods=["GET", "POST"])
def add():

    if request.method == "POST":

        title = request.form["title"].strip()

        amount = float(
            request.form["amount"]
        )

        category = request.form["category"]

        transaction_type = request.form["type"]

        date = request.form["date"]


        conn = get_db_connection()

        conn.execute("""
            INSERT INTO transactions
            (
                title,
                amount,
                category,
                type,
                date
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            title,
            amount,
            category,
            transaction_type,
            date
        ))


        conn.commit()
        conn.close()


        return redirect(
            url_for("history")
        )


    return render_template(
        "add.html"
    )


# =========================================================
# TRANSACTION HISTORY
# =========================================================

@app.route("/history")
def history():

    search = request.args.get(
        "search",
        ""
    ).strip()

    selected_type = request.args.get(
        "type",
        ""
    )

    selected_category = request.args.get(
        "category",
        ""
    )

    from_date = request.args.get(
        "from_date",
        ""
    )

    to_date = request.args.get(
        "to_date",
        ""
    )

    selected_sort = request.args.get(
        "sort",
        "newest"
    )


    conn = get_db_connection()


    # -----------------------------------------------------
    # CATEGORIES
    # -----------------------------------------------------

    categories = conn.execute("""
        SELECT DISTINCT category
        FROM transactions
        ORDER BY category COLLATE NOCASE
    """).fetchall()


    # -----------------------------------------------------
    # BASE QUERY
    # -----------------------------------------------------

    query = """
        SELECT *
        FROM transactions
        WHERE 1 = 1
    """

    parameters = []


    # -----------------------------------------------------
    # SEARCH
    # -----------------------------------------------------

    if search:

        query += """
            AND (
                title LIKE ?
                OR category LIKE ?
            )
        """

        search_value = f"%{search}%"

        parameters.extend([
            search_value,
            search_value
        ])


    # -----------------------------------------------------
    # TYPE
    # -----------------------------------------------------

    if selected_type:

        query += """
            AND type = ?
        """

        parameters.append(
            selected_type
        )


    # -----------------------------------------------------
    # CATEGORY
    # -----------------------------------------------------

    if selected_category:

        query += """
            AND category = ?
        """

        parameters.append(
            selected_category
        )


    # -----------------------------------------------------
    # FROM DATE
    # -----------------------------------------------------

    if from_date:

        query += """
            AND date >= ?
        """

        parameters.append(
            from_date
        )


    # -----------------------------------------------------
    # TO DATE
    # -----------------------------------------------------

    if to_date:

        query += """
            AND date <= ?
        """

        parameters.append(
            to_date
        )


    # -----------------------------------------------------
    # SORT
    # -----------------------------------------------------

    sort_options = {

        "newest":
            "date DESC, id DESC",

        "oldest":
            "date ASC, id ASC",

        "highest":
            "amount DESC",

        "lowest":
            "amount ASC",

        "title_az":
            "title COLLATE NOCASE ASC",

        "title_za":
            "title COLLATE NOCASE DESC"
    }


    order_by = sort_options.get(
        selected_sort,
        "date DESC, id DESC"
    )


    query += f"""
        ORDER BY {order_by}
    """


    transactions = conn.execute(
        query,
        parameters
    ).fetchall()


    conn.close()


    return render_template(
        "history.html",

        transactions=transactions,

        categories=categories,

        search=search,

        selected_type=selected_type,

        selected_category=selected_category,

        from_date=from_date,

        to_date=to_date,

        selected_sort=selected_sort
    )


# =========================================================
# EDIT TRANSACTION
# =========================================================

@app.route(
    "/edit/<int:id>",
    methods=["GET", "POST"]
)
def edit(id):

    conn = get_db_connection()


    transaction = conn.execute("""
        SELECT *
        FROM transactions
        WHERE id = ?
    """, (id,)).fetchone()


    if transaction is None:

        conn.close()

        return "Transaction not found", 404


    if request.method == "POST":

        title = request.form["title"].strip()

        amount = float(
            request.form["amount"]
        )

        category = request.form["category"]

        transaction_type = request.form["type"]

        date = request.form["date"]


        conn.execute("""
            UPDATE transactions

            SET
                title = ?,
                amount = ?,
                category = ?,
                type = ?,
                date = ?

            WHERE id = ?
        """, (
            title,
            amount,
            category,
            transaction_type,
            date,
            id
        ))


        conn.commit()
        conn.close()


        return redirect(
            url_for("history")
        )


    conn.close()


    return render_template(
        "edit.html",
        transaction=transaction
    )


# =========================================================
# DELETE TRANSACTION
# =========================================================

@app.route("/delete/<int:id>")
def delete(id):

    conn = get_db_connection()


    conn.execute("""
        DELETE FROM transactions
        WHERE id = ?
    """, (id,))


    conn.commit()
    conn.close()


    return redirect(
        url_for("history")
    )


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True
    ) 