import os
import secrets
from functools import wraps
from datetime import datetime

import sqlite3

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    abort,
)

from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)

# =========================================================
# SECRET KEY
# =========================================================
# Reads from the environment in production. Falls back to a
# random key for local development so the app still runs
# without extra setup -- but that means sessions won't
# survive a restart unless SECRET_KEY is actually set.

app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


# =========================================================
# CREATE / MIGRATE TABLES
# =========================================================

def create_table():

    conn = get_db_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            type TEXT NOT NULL,
            date TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    # Migration safety net: if transactions already existed
    # from before accounts were added, give it a user_id
    # column instead of failing.
    existing_columns = [
        row["name"]
        for row in conn.execute(
            "PRAGMA table_info(transactions)"
        ).fetchall()
    ]

    if "user_id" not in existing_columns:
        conn.execute(
            "ALTER TABLE transactions ADD COLUMN user_id INTEGER"
        )

    conn.commit()
    conn.close()


create_table()


# =========================================================
# CSRF PROTECTION
# =========================================================

def get_csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)
    return session["csrf_token"]


app.jinja_env.globals["csrf_token"] = get_csrf_token


@app.before_request
def csrf_protect():

    if request.method == "POST":

        submitted_token = request.form.get("csrf_token")
        session_token = session.get("csrf_token")

        if not session_token or submitted_token != session_token:
            abort(400, description="Invalid or missing CSRF token.")


# =========================================================
# LOGIN REQUIRED DECORATOR
# =========================================================

def login_required(view):

    @wraps(view)
    def wrapped(*args, **kwargs):

        if "user_id" not in session:
            return redirect(
                url_for("login", next=request.path)
            )

        return view(*args, **kwargs)

    return wrapped


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
# REGISTER
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if "user_id" in session:
        return redirect(url_for("index"))

    error = None

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not username or not password:
            error = "Username and password are required."

        elif len(password) < 6:
            error = "Password must be at least 6 characters."

        elif password != confirm_password:
            error = "Passwords do not match."

        else:

            conn = get_db_connection()

            existing_user = conn.execute(
                "SELECT id FROM users WHERE username = ?",
                (username,)
            ).fetchone()

            if existing_user:

                error = "That username is already taken."

                conn.close()

            else:

                conn.execute("""
                    INSERT INTO users
                    (username, password_hash, created_at)
                    VALUES (?, ?, ?)
                """, (
                    username,
                    generate_password_hash(password),
                    datetime.utcnow().isoformat()
                ))

                conn.commit()

                new_user = conn.execute(
                    "SELECT id FROM users WHERE username = ?",
                    (username,)
                ).fetchone()

                conn.close()

                session.clear()
                session["user_id"] = new_user["id"]
                session["username"] = username

                return redirect(url_for("index"))

    return render_template(
        "register.html",
        error=error
    )


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if "user_id" in session:
        return redirect(url_for("index"))

    error = None

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        conn = get_db_connection()

        user = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        conn.close()

        if user is None or not check_password_hash(
            user["password_hash"], password
        ):
            error = "Invalid username or password."

        else:

            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]

            next_page = request.args.get("next")

            return redirect(next_page or url_for("index"))

    return render_template(
        "login.html",
        error=error
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/")
@login_required
def index():

    user_id = session["user_id"]

    conn = get_db_connection()


    # -----------------------------------------------------
    # TOTAL INCOME
    # -----------------------------------------------------

    income = conn.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE type = 'Income' AND user_id = ?
    """, (user_id,)).fetchone()[0]


    # -----------------------------------------------------
    # TOTAL EXPENSE
    # -----------------------------------------------------

    expense = conn.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE type = 'Expense' AND user_id = ?
    """, (user_id,)).fetchone()[0]


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
        WHERE user_id = ?
    """, (user_id,)).fetchone()[0]


    # -----------------------------------------------------
    # INCOME TRANSACTION COUNT
    # -----------------------------------------------------

    income_count = conn.execute("""
        SELECT COUNT(*)
        FROM transactions
        WHERE type = 'Income' AND user_id = ?
    """, (user_id,)).fetchone()[0]


    # -----------------------------------------------------
    # EXPENSE TRANSACTION COUNT
    # -----------------------------------------------------

    expense_count = conn.execute("""
        SELECT COUNT(*)
        FROM transactions
        WHERE type = 'Expense' AND user_id = ?
    """, (user_id,)).fetchone()[0]


    # -----------------------------------------------------
    # AVERAGE EXPENSE
    # -----------------------------------------------------

    average_expense = conn.execute("""
        SELECT COALESCE(AVG(amount), 0)
        FROM transactions
        WHERE type = 'Expense' AND user_id = ?
    """, (user_id,)).fetchone()[0]


    # -----------------------------------------------------
    # AVERAGE INCOME
    # -----------------------------------------------------

    average_income = conn.execute("""
        SELECT COALESCE(AVG(amount), 0)
        FROM transactions
        WHERE type = 'Income' AND user_id = ?
    """, (user_id,)).fetchone()[0]


    # -----------------------------------------------------
    # LARGEST EXPENSE
    # -----------------------------------------------------

    largest_expense = conn.execute("""
        SELECT COALESCE(MAX(amount), 0)
        FROM transactions
        WHERE type = 'Expense' AND user_id = ?
    """, (user_id,)).fetchone()[0]


    # -----------------------------------------------------
    # LARGEST INCOME
    # -----------------------------------------------------

    largest_income = conn.execute("""
        SELECT COALESCE(MAX(amount), 0)
        FROM transactions
        WHERE type = 'Income' AND user_id = ?
    """, (user_id,)).fetchone()[0]


    # -----------------------------------------------------
    # RECENT TRANSACTIONS
    # -----------------------------------------------------

    transactions = conn.execute("""
        SELECT *
        FROM transactions
        WHERE user_id = ?
        ORDER BY date DESC, id DESC
        LIMIT 10
    """, (user_id,)).fetchall()


    # -----------------------------------------------------
    # EXPENSE BY CATEGORY
    # -----------------------------------------------------

    category_data = conn.execute("""
        SELECT
            category,
            SUM(amount) AS total
        FROM transactions
        WHERE type = 'Expense' AND user_id = ?
        GROUP BY category
        ORDER BY total DESC
    """, (user_id,)).fetchall()


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
@login_required
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
                user_id,
                title,
                amount,
                category,
                type,
                date
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            session["user_id"],
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
@login_required
def history():

    user_id = session["user_id"]

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
        WHERE user_id = ?
        ORDER BY category COLLATE NOCASE
    """, (user_id,)).fetchall()


    # -----------------------------------------------------
    # BASE QUERY
    # -----------------------------------------------------

    query = """
        SELECT *
        FROM transactions
        WHERE user_id = ?
    """

    parameters = [user_id]


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
@login_required
def edit(id):

    user_id = session["user_id"]

    conn = get_db_connection()


    transaction = conn.execute("""
        SELECT *
        FROM transactions
        WHERE id = ? AND user_id = ?
    """, (id, user_id)).fetchone()


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

            WHERE id = ? AND user_id = ?
        """, (
            title,
            amount,
            category,
            transaction_type,
            date,
            id,
            user_id
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

@app.route("/delete/<int:id>", methods=["POST"])
@login_required
def delete(id):

    user_id = session["user_id"]

    conn = get_db_connection()


    conn.execute("""
        DELETE FROM transactions
        WHERE id = ? AND user_id = ?
    """, (id, user_id))


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
