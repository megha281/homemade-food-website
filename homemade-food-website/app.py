from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import boto3
from botocore.exceptions import ClientError
from datetime import datetime
import uuid
import json

app = Flask(__name__)
app.secret_key = "secret123"

# ================= AWS DYNAMODB SETUP =================

# Update 'us-east-1' to your specific AWS region
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
users_table = dynamodb.Table('users')
orders_table = dynamodb.Table('orders')

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

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password)

        try:
            # DynamoDB put_item with condition to ensure username is unique
            users_table.put_item(
                Item={
                    'username': username,
                    'email': email,
                    'password': hashed_password
                },
                ConditionExpression='attribute_not_exists(username)'
            )
            return redirect(url_for('login'))
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                return render_template("signup.html", error="Username already exists")
            else:
                return render_template("signup.html", error="Database error occurred")

    return render_template("signup.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        try:
            response = users_table.get_item(Key={'username': username})
            user = response.get('Item')

            if not user:
                return render_template("login.html", error="User not found")

            if not check_password_hash(user['password'], password):
                return render_template("login.html", error="Invalid password")

            session['logged_in'] = True
            session['username'] = username
            session['cart'] = []
            return redirect(url_for('home'))
            
        except ClientError:
            return render_template("login.html", error="Connection error")

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
    return render_template("veg_pickles.html", products=products['veg_pickles'])

@app.route('/non_veg_pickles')
def non_veg_pickles():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template("non_veg_pickles.html", products=products['non_veg_pickles'])

@app.route('/snacks')
def snacks():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template("snacks.html", products=products['snacks'])

@app.route('/cart')
def cart():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template("cart.html")

# ================= CHECKOUT =================

@app.route('/checkout', methods=['GET', 'POST'])
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

        try:
            orders_table.put_item(
                Item={
                    'order_id': order_id,
                    'username': session['username'],
                    'name': name,
                    'address': address,
                    'phone': phone,
                    'items': cart_data,
                    'total_amount': total_amount,
                    'payment_method': payment,
                    'timestamp': datetime.now().isoformat()
                }
            )
            return redirect(url_for("sucess"))
        except ClientError as e:
            print(f"Error saving order: {e}")
            return "There was an error processing your order."

    return render_template("checkout.html")

# ================= SUCCESS =================

@app.route('/sucess')
def sucess():
    return render_template("sucess.html")

if __name__ == "__main__":
    app.run(debug=True)
