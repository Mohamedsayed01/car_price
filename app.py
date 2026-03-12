from flask import Flask, render_template, request, redirect, session, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import re
import random
from datetime import datetime, timedelta
import uuid

app = Flask(__name__)
app.secret_key = "carvo_secret_very_secure_2026"

reset_tokens = {}  # token → {'username': ..., 'expires': ...}

def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            prediction_count INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_db():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
def home():
    logged_in = "user" in session
    return render_template("home.html", logged_in=logged_in)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        terms = request.form.get("terms")

        if not all([full_name, email, username, password, confirm]):
            flash("All fields are required!", "error")
            return redirect(url_for("register"))

        if password != confirm:
            flash("Passwords do not match!", "error")
            return redirect(url_for("register"))

        if len(password) < 8:
            flash("Password must be at least 8 characters!", "error")
            return redirect(url_for("register"))

        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash("Invalid email format!", "error")
            return redirect(url_for("register"))

        if not terms:
            flash("You must agree to the terms!", "error")
            return redirect(url_for("register"))

        password_hash = generate_password_hash(password)
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = get_db()
        c = conn.cursor()
        try:
            c.execute("""
                INSERT INTO users (username, email, full_name, password_hash, created_at, prediction_count)
                VALUES (?, ?, ?, ?, ?, 0)
            """, (username, email, full_name, password_hash, created_at))
            conn.commit()
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Username or email already exists!", "error")
        finally:
            conn.close()

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user"] = username
            flash("Login successful!", "success")
            return redirect(url_for("predict"))
        else:
            flash("Invalid username or password!", "error")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("Logged out successfully.", "success")
    return redirect(url_for("home"))

@app.route("/predict", methods=["GET", "POST"])
def predict():
    if "user" not in session:
        flash("Please log in to make a prediction.", "error")
        return redirect(url_for("login"))

    if request.method == "POST":
        try:
            year = int(request.form.get("year"))
            km_driven = int(request.form.get("km_driven"))

            conn = get_db()
            c = conn.cursor()
            c.execute("UPDATE users SET prediction_count = prediction_count + 1 WHERE username = ?", (session["user"],))
            conn.commit()
            conn.close()

            price = random.randint(280000, 1400000)
            price = round(price / 1000) * 1000

            return render_template("result.html", price=price)
        except:
            flash("Invalid input. Please check the values.", "error")

    return render_template("predict.html")

@app.route("/profile")
def profile():
    if "user" not in session:
        flash("Please log in first.", "error")
        return redirect(url_for("login"))

    username = session["user"]
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT username, full_name, email, created_at, prediction_count 
        FROM users 
        WHERE username = ?
    """, (username,))
    user = c.fetchone()
    conn.close()

    if not user:
        flash("User not found.", "error")
        return redirect(url_for("logout"))

    profile_info = {
        "username": user["username"],
        "full_name": user["full_name"],
        "email": user["email"],
        "created_at": user["created_at"],
        "prediction_count": user["prediction_count"] if user["prediction_count"] is not None else 0
    }

    return render_template("profile.html", profile=profile_info)

@app.route("/edit_profile", methods=["GET", "POST"])
def edit_profile():
    if "user" not in session:
        flash("Please log in first.", "error")
        return redirect(url_for("login"))

    username = session["user"]
    conn = get_db()
    c = conn.cursor()

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip()
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not all([full_name, email]):
            flash("Full name and email are required!", "error")
            conn.close()
            return redirect(url_for("edit_profile"))

        if new_password and new_password != confirm_password:
            flash("New passwords do not match!", "error")
            conn.close()
            return redirect(url_for("edit_profile"))

        if new_password and len(new_password) < 8:
            flash("New password must be at least 8 characters!", "error")
            conn.close()
            return redirect(url_for("edit_profile"))

        if new_password:
            password_hash = generate_password_hash(new_password)
            c.execute("""
                UPDATE users 
                SET full_name = ?, email = ?, password_hash = ? 
                WHERE username = ?
            """, (full_name, email, password_hash, username))
        else:
            c.execute("""
                UPDATE users 
                SET full_name = ?, email = ? 
                WHERE username = ?
            """, (full_name, email, username))

        conn.commit()
        conn.close()

        flash("Profile updated successfully!", "success")
        return redirect(url_for("profile"))

    c.execute("SELECT username, full_name, email FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    conn.close()

    if not user:
        flash("User not found.", "error")
        return redirect(url_for("logout"))

    return render_template("edit_profile.html", profile=user)

@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip()

        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT username FROM users WHERE email = ?", (email,))
        user = c.fetchone()
        conn.close()

        if user:
            token = str(uuid.uuid4())
            expires = datetime.now() + timedelta(hours=1)
            reset_tokens[token] = {
                "username": user["username"],
                "expires": expires
            }

            reset_link = url_for("reset_password", token=token, _external=True)
            print(f"[RESET LINK for {email}]: {reset_link}")

            flash("If an account exists with this email, you will receive a password reset link.", "success")
        else:
            flash("If an account exists with this email, you will receive a password reset link.", "success")

        return redirect(url_for("login"))

    return render_template("forgot_password.html")

@app.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if token not in reset_tokens:
        flash("Invalid or expired reset link.", "error")
        return redirect(url_for("login"))

    data = reset_tokens[token]
    if datetime.now() > data["expires"]:
        del reset_tokens[token]
        flash("Reset link has expired.", "error")
        return redirect(url_for("login"))

    if request.method == "POST":
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not new_password or new_password != confirm_password:
            flash("Passwords do not match or are empty!", "error")
            return redirect(url_for("reset_password", token=token))

        if len(new_password) < 8:
            flash("Password must be at least 8 characters!", "error")
            return redirect(url_for("reset_password", token=token))

        password_hash = generate_password_hash(new_password)

        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE users SET password_hash = ? WHERE username = ?", (password_hash, data["username"]))
        conn.commit()
        conn.close()

        del reset_tokens[token]
        flash("Password reset successfully! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("reset_password.html")

if __name__ == "__main__":
    app.run(debug=True)