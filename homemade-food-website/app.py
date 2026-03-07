from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime
import json
import uuid

app = Flask(__name__)
app.secret_key = "secret123"


# ================= DATABASE SETUP =================

def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        username TEXT PRIMARY KEY,
        email TEXT,
        password TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders(
        order_id TEXT,
        username TEXT,
        name TEXT,
        address TEXT,
        phone TEXT,
        items TEXT,
        total_amount TEXT,
        payment_method TEXT,
        timestamp TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()


# ================= PRODUCT DATA =================

products = {

'non_veg_pickles': [
{'id': 1, 'name': 'Chicken Pickle', 'weights': {'250': 600, '500': 1200, '1000': 1800}},
{'id': 2, 'name': 'Fish Pickle', 'weights': {'250': 200, '500': 400, '1000': 800}},
{'id': 3, 'name': 'Gongura Mutton', 'weights': {'250': 400, '500': 800, '1000': 1600}},
{'id': 4, 'name': 'Mutton Pickle', 'weights': {'250': 400, '500': 800, '1000': 1600}},
{'id': 5, 'name': 'Gongura Prawns', 'weights': {'250': 600, '500': 1200, '1000': 1800}},
{'id': 6, 'name': 'Chicken Pickle (Gongura)', 'weights': {'250': 350, '500': 700, '1000': 1050}}
],

'veg_pickles': [
{'id': 7, 'name': 'Traditional Mango Pickle', 'weights': {'250': 150, '500': 280, '1000': 500}},
{'id': 8, 'name': 'Zesty Lemon Pickle', 'weights': {'250': 120, '500': 220, '1000': 400}},
{'id': 9, 'name': 'Tomato Pickle', 'weights': {'250': 130, '500': 240, '1000': 450}},
{'id': 10, 'name': 'Kakarakaya Pickle', 'weights': {'250': 130, '500': 240, '1000': 450}},
{'id': 11, 'name': 'Chintakaya Pickle', 'weights': {'250': 130, '500': 240, '1000': 450}},
{'id': 12, 'name': 'Spicy Pandu Mirchi', 'weights': {'250': 130, '500': 240, '1000': 450}}
],

'snacks': [
{'id': 13, 'name': 'Banana Chips', 'weights': {'250': 300, '500': 600, '1000': 800}},
{'id': 14, 'name': 'Crispy Aam-Papad', 'weights': {'250': 150, '500': 300, '1000': 600}},
{'id': 15, 'name': 'Crispy Chekka Pakodi', 'weights': {'250': 50, '500': 100, '1000': 200}},
{'id': 16, 'name': 'Boondhi Acchu', 'weights': {'250': 300, '500': 600, '1000': 900}},
{'id': 17, 'name': 'Chekkalu', 'weights': {'250': 350, '500': 700, '1000': 1000}},
{'id': 18, 'name': 'Ragi Laddu', 'weights': {'250': 350, '500': 700, '1000': 1000}}
]

}


# ================= AUTH ROUTES =================

@app.route('/')
def index():
    return render_template("index.html")


@app.route('/signup', methods=['GET','POST'])
def signup():

    if request.method == 'POST':

        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE username=?", (username,))
        user = cursor.fetchone()

        if user:
            return render_template("signup.html", error="Username already exists")

        hashed_password = generate_password_hash(password)

        cursor.execute(
        "INSERT INTO users VALUES (?,?,?)",
        (username,email,hashed_password)
        )

        conn.commit()
        conn.close()

        return redirect(url_for('login'))

    return render_template("signup.html")


@app.route('/login', methods=['GET','POST'])
def login():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE username=?", (username,))
        user = cursor.fetchone()

        conn.close()

        if not user:
            return render_template("login.html", error="User not found")

        if not check_password_hash(user[2], password):
            return render_template("login.html", error="Invalid password")

        session['logged_in'] = True
        session['username'] = username
        session['cart'] = []

        return redirect(url_for('home'))

    return render_template("login.html")


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ================= PRODUCT PAGES =================

@app.route('/home')
def home():

    if not session.get('logged_in'):
        return redirect(url_for('login'))

    return render_template("home.html")


@app.route('/veg_pickles')
def veg_pickles():

    if not session.get('logged_in'):
        return redirect(url_for('login'))

    return render_template(
        "veg_pickles.html",
        products=products['veg_pickles']
    )


@app.route('/non_veg_pickles')
def non_veg_pickles():

    if not session.get('logged_in'):
        return redirect(url_for('login'))

    return render_template(
        "non_veg_pickles.html",
        products=products['non_veg_pickles']
    )


@app.route('/snacks')
def snacks():

    if not session.get('logged_in'):
        return redirect(url_for('login'))

    return render_template(
        "snacks.html",
        products=products['snacks']
    )


# ================= CART =================

@app.route('/cart')
def cart():

    if not session.get('logged_in'):
        return redirect(url_for('login'))

    return render_template("cart.html")


# ================= CHECKOUT =================

@app.route('/checkout', methods=['GET','POST'])
def checkout():

    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':

        name = request.form['name']
        address = request.form['address']
        phone = request.form['phone']
        payment = request.form['payment']

        cart_data = request.form['cart_data']
        total_amount = request.form['total_amount']

        order_id = str(uuid.uuid4())

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?)
        """,(
        order_id,
        session['username'],
        name,
        address,
        phone,
        cart_data,
        total_amount,
        payment,
        datetime.now().isoformat()
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("sucess"))

    return render_template("checkout.html")


# ================= SUCCESS =================

@app.route('/sucess')
def sucess():
    return render_template("sucess.html")


# ================= RUN SERVER =================

if __name__ == "__main__":
    app.run(debug=True)