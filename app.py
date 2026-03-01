from flask import Flask, render_template, request, redirect, session, url_for
import random

app = Flask(__name__)
app.secret_key = "carvo_secret_1234"

# Simple in-memory user storage
users = {}

@app.route("/")
def home():
    return render_template("home.html", logged_in=session.get("user"))

# Register
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username in users:
            return render_template("register.html", msg="❌ Username already exists")
        users[username] = password
        return redirect("/login")

    return render_template("register.html")

# Login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username in users and users[username] == password:
            session["user"] = username
            return redirect("/predict")
        return render_template("login.html", msg="❌ Invalid credentials")

    return render_template("login.html")

# Logout
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/")

# Predict (protected)
@app.route("/predict", methods=["GET", "POST"])
def predict():
    if not session.get("user"):
        return redirect("/login")

    if request.method == "POST":
        fake_price = random.randint(300000, 900000)
        return render_template("result.html", price=fake_price)

    return render_template("predict.html", logged_in=session.get("user"))

if __name__ == "__main__":
    app.run(debug=True)
