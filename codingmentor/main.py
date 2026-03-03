from flask import Flask, render_template, request, redirect, session, jsonify
import sqlite3
import ast
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "supersecretkey123"
app.config['SESSION_COOKIE_SECURE'] = False


# ---------------- DATABASE SETUP ----------------

def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # USERS TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fullname TEXT,
        email TEXT,
        userid TEXT UNIQUE,
        password TEXT
    )
    """)

    # ADMINS TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        adminid TEXT UNIQUE,
        password TEXT
    )
    """)

    # ANALYSIS HISTORY TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS analysis_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        userid TEXT,
        code TEXT,
        concept TEXT,
        analogy TEXT,
        hint TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # CREATE DEFAULT ADMIN (ONLY ONCE)
    cursor.execute("SELECT * FROM admins WHERE adminid=?", ("admin1",))
    admin = cursor.fetchone()

    if not admin:
        hashed_admin = generate_password_hash("admin123")
        cursor.execute(
            "INSERT INTO admins (adminid, password) VALUES (?, ?)",
            ("admin1", hashed_admin)
        )

    conn.commit()
    conn.close()


init_db()


# ---------------- HOME ----------------

@app.route("/")
def home():
    return render_template("login.html")


# ---------------- USER SIGNUP ----------------

@app.route("/signup", methods=["POST"])
def signup():
    fullname = request.form.get("fullname")
    email = request.form.get("email")
    userid = request.form.get("userid")
    password = request.form.get("password")

    hashed_password = generate_password_hash(password)

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO users (fullname, email, userid, password) VALUES (?, ?, ?, ?)",
            (fullname, email, userid, hashed_password)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return "User ID already exists!"

    conn.close()

    session.clear()
    session["user"] = userid
    return redirect("/dashboard")


# ---------------- USER LOGIN ----------------

@app.route("/user_login", methods=["POST"])
def user_login():
    userid = request.form.get("userid")
    password = request.form.get("password")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT password FROM users WHERE userid=?", (userid,))
    user = cursor.fetchone()
    conn.close()

    if user and check_password_hash(user[0], password):
        session.clear()
        session["user"] = userid
        return redirect("/dashboard")
    else:
        return "Invalid User Credentials!"


# ---------------- ADMIN LOGIN ----------------

@app.route("/admin_login", methods=["POST"])
def admin_login():
    adminid = request.form.get("adminid")
    adminpass = request.form.get("adminpass")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT password FROM admins WHERE adminid=?", (adminid,))
    admin = cursor.fetchone()
    conn.close()

    if admin and check_password_hash(admin[0], adminpass):
        session.clear()
        session["admin"] = adminid
        return redirect("/admin_dashboard")
    else:
        return "Invalid Admin Credentials!"


# ---------------- USER DASHBOARD ----------------

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT code, concept, timestamp
        FROM analysis_history
        WHERE userid=?
        ORDER BY id DESC
        LIMIT 5
    """, (session["user"],))

    history = cursor.fetchall()
    conn.close()

    return render_template("dashboard.html",
                           user=session["user"],
                           history=history)


# ---------------- ADMIN DASHBOARD ----------------

@app.route("/admin_dashboard")
def admin_dashboard():
    if "admin" not in session:
        return redirect("/")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT fullname, email, userid FROM users")
    users = cursor.fetchall()
    conn.close()

    return render_template("admin.html",
                           admin=session["admin"],
                           users=users)


# ---------------- ANALYZER ----------------

@app.route("/analyze", methods=["POST"])
def analyze():

    if "user" not in session:
        return jsonify({"concept": "Login required", "analogy": "", "hint": ""})

    code = request.form.get("code")

    concept = ""
    analogy = ""
    hint = ""

    # Syntax Check
    try:
        compile(code, "<string>", "exec")
        ast.parse(code)
    except SyntaxError as e:
        concept = f"Syntax Error: {e.msg}"
        analogy = "Like writing a sentence with broken grammar."
        hint = "Check colons, indentation, parentheses."
        return jsonify({"concept": concept, "analogy": analogy, "hint": hint})

     # ---------- 25 LOGIC RULES ----------#

    if "while True" in code and "break" not in code:
        concept = "Possible infinite loop."
        analogy = "Like a treadmill that never stops."
        hint = "Add break condition."

    elif "==" in code and "if" not in code:
        concept = "Comparison used outside condition."
        analogy = "Asking a question but not listening to answer."
        hint = "Use comparison inside if statement."

    elif "for" in code and "append(" not in code and "[" in code:
        concept = "Loop may not store results."
        analogy = "Collecting fruits but no basket."
        hint = "Use list.append()."

    elif "while" in code and "+=" not in code and "-=" not in code:
        concept = "Loop counter may not change."
        analogy = "Walking but not moving forward."
        hint = "Update loop variable."

    elif "input(" in code and "strip()" not in code:
        concept = "Input may contain unwanted spaces."
        analogy = "Writing with extra blank lines."
        hint = "Use .strip()."

    elif "open(" in code and "close()" not in code and "with open" not in code:
        concept = "File not properly closed."
        analogy = "Opening door and leaving it open."
        hint = "Use with open()."

    elif "list(" in code and "[]" in code:
        concept = "Redundant list creation."
        analogy = "Buying two notebooks for same subject."
        hint = "Use either list() or []."

    elif "dict()" in code and "{}" in code:
        concept = "Redundant dictionary creation."
        analogy = "Two keys for same lock."
        hint = "Use either dict() or {}."

    elif "try:" in code and "except" not in code:
        concept = "Try block without except."
        analogy = "Wearing helmet but no seatbelt."
        hint = "Add except block."

    elif "except Exception" in code:
        concept = "Generic exception caught."
        analogy = "Catching all fish blindly."
        hint = "Catch specific exceptions."

    elif "==" in code and "True" in code:
        concept = "Unnecessary boolean comparison."
        analogy = "Checking if light is equal to ON."
        hint = "Use condition directly."

    elif "len(" in code and "== 0" in code:
        concept = "Checking empty list inefficiently."
        analogy = "Measuring box to see if empty."
        hint = "Use if not list_name."

    elif "range(len(" in code:
        concept = "Index-based loop detected."
        analogy = "Counting steps instead of walking."
        hint = "Use direct iteration."

    elif "map(" in code and "lambda" not in code:
        concept = "Map used without lambda."
        analogy = "Machine without instruction."
        hint = "Provide function to map()."

    elif "filter(" in code and "lambda" not in code:
        concept = "Filter used without condition."
        analogy = "Filtering water without filter."
        hint = "Provide condition."

    elif ".sort(" in code and "=" in code:
        concept = "Sort returns None."
        analogy = "Rearranging books but expecting new shelf."
        hint = "Use sorted() if needed."

    elif " is " in code and "==" in code:
        concept = "Possible misuse of 'is' operator."
        analogy = "Checking identity instead of equality."
        hint = "Use == for value comparison."

    elif "input(" in code and "=" not in code:
        concept = "Input not stored."
        analogy = "Receiving call but not saving number."
        hint = "Assign input to variable."

    elif code.strip().startswith("return"):
        concept = "Return outside function."
        analogy = "Leaving class without entering."
        hint = "Use return inside def block."

    elif "class " in code and "self" not in code:
        concept = "Class without self reference."
        analogy = "Owner not knowing their house."
        hint = "Use self inside methods."

    elif "__init__" in code and "self" not in code:
        concept = "Constructor missing self."
        analogy = "Building without foundation."
        hint = "Add self parameter."

    elif "if __name__" in code and "__main__" not in code:
        concept = "Incorrect main check."
        analogy = "Door without proper lock."
        hint = "Use if __name__ == '__main__':"

    elif "break" in code and "for" not in code and "while" not in code:
        concept = "Break outside loop."
        analogy = "Emergency exit without building."
        hint = "Use break inside loop."

    elif "continue" in code and "for" not in code and "while" not in code:
        concept = "Continue outside loop."
        analogy = "Skipping step without walking."
        hint = "Use inside loop."

    elif "input(" in code and "+" in code and "int(" not in code:
        concept = "String concatenation instead of addition."
        analogy = "Joining numbers as text."
        hint = "Convert input to int."

    elif "time.sleep" in code and "import time" not in code:
        concept = "Time module not imported."
        analogy = "Using tool not in toolbox."
        hint = "Add import time."

    elif "math." in code and "import math" not in code:
        concept = "Math module not imported."
        analogy = "Using calculator without batteries."
        hint = "Add import math."

    elif "random." in code and "import random" not in code:
        concept = "Random module not imported."
        analogy = "Rolling dice without dice."
        hint = "Add import random."

    else:
        concept = "Structure looks logically acceptable."
        analogy = "Building appears strong."
        hint = "Test edge cases."
    # Save history
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO analysis_history (userid, code, concept, analogy, hint)
        VALUES (?, ?, ?, ?, ?)
    """, (session["user"], code, concept, analogy, hint))

    conn.commit()
    conn.close()

    return jsonify({"concept": concept, "analogy": analogy, "hint": hint})


# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)