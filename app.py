from flask import Flask, render_template, request, flash, redirect, url_for, jsonify
from flask_socketio import SocketIO
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired
from flask_wtf import FlaskForm
from flask_login import LoginManager, UserMixin, login_user, login_required
import sqlite3

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key'  # Add a secret key for security
socketio = SocketIO(app)  # Initialize SocketIO with your Flask app

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# SQLite setup
def setup_sqlite():
    with sqlite3.connect("database.db") as con:
        con.execute(
            "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, password TEXT, email TEXT)"
        )

def setup_sqlite_driver():
    with sqlite3.connect("driver.db") as con:
        con.execute(
            "CREATE TABLE IF NOT EXISTS drivers (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, password TEXT, email TEXT, vehicle_model TEXT)"
        )

def setup_sqlite_trips():
    with sqlite3.connect("trips.db") as con:
        con.execute(
            "CREATE TABLE IF NOT EXISTS trips (id INTEGER PRIMARY KEY AUTOINCREMENT, pickup_location TEXT, dropoff_location TEXT, pickup_time TEXT, driver_id INTEGER)"
        )

# User model
class User(UserMixin):
    def __init__(self, id, username, password, email):
        self.id = id
        self.username = username
        self.password = password
        self.email = email

# Load user from SQLite
@login_manager.user_loader
def load_user(user_id):
    con = sqlite3.connect("database.db")
    cur = con.cursor()
    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user_data = cur.fetchone()
    if user_data:
        return User(*user_data)
    return None

# Registration form for users
class UserRegistrationForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired()])
    submit = SubmitField("Register as User")

# Registration form for drivers
class DriverRegistrationForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired()])
    vehicle_model = StringField("Vehicle Model", validators=[DataRequired()])
    submit = SubmitField("Register as Driver")

# Login form
class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")

@app.route('/')
def index():
    return render_template('index.html')

@app.route("/user")
def user():
    return render_template("user.html")

@app.route("/drive")
def drive():
    return render_template("drive.html")

# Registration route for users
@app.route("/register_user", methods=["GET", "POST"])
def register_user():
    form = UserRegistrationForm()
    if form.validate_on_submit():
        flash("User registration successful!", "success")
        return redirect(url_for("login"))
    return render_template("register_user.html", form=form)

# Registration route for drivers
@app.route("/register_driver", methods=["GET", "POST"])
def register_driver():
    form = DriverRegistrationForm()
    if form.validate_on_submit():
        flash("Driver registration successful!", "success")
        with sqlite3.connect("driver.db") as con:
            cur = con.cursor()
            cur.execute("INSERT INTO drivers (username, password, email, vehicle_model) VALUES (?, ?, ?, ?)",
                        (form.username.data, form.password.data, form.email.data, form.vehicle_model.data))
        return redirect(url_for("login"))
    return render_template("register_driver.html", form=form)

# Login route
@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        # Check if the user exists in the users table
        con_users = sqlite3.connect("database.db")
        cur_users = con_users.cursor()
        cur_users.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user_data = cur_users.fetchone()

        # Check if the user exists in the drivers table
        con_drivers = sqlite3.connect("driver.db")
        cur_drivers = con_drivers.cursor()
        cur_drivers.execute("SELECT * FROM drivers WHERE username = ? AND password = ?", (username, password))
        driver_data = cur_drivers.fetchone()

        if user_data:
            # If the user exists in the users table, log them in
            user = User(*user_data)
            login_user(user)
            flash("Login successful as User!", "success")
            return redirect(url_for("destination"))
        elif driver_data:
            # If the user exists in the drivers table, log them in
            flash("Login successful as Driver!", "success")
            return redirect(url_for("driver"))
        else:
            # If neither user nor driver exists, show an error message
            flash("Invalid username or password", "error")

    return render_template("login.html", form=form)

@app.route("/logout")
@login_required
def logout():
    # Handle user logout here (if using Flask-Login)
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))

@app.route('/driver')
def driver():
    # Retrieve data from trips table
    with sqlite3.connect("trips.db") as con:
        cur = con.cursor()
        cur.execute("SELECT * FROM trips")
        trips_data = cur.fetchall()

    # Store data in the drivers table
    with sqlite3.connect("driver.db") as con:
        cur = con.cursor()
        for trip in trips_data:
            cur.execute("INSERT INTO drivers (username, password, email, vehicle_model) VALUES (?, ?, ?, ?)",
                        (trip[1], 'password_placeholder', 'email_placeholder', 'vehicle_model_placeholder'))

    return render_template('driver.html', orders=trips_data)

@app.route('/destination', methods=["GET", "POST"])
def destination():
    if request.method == "POST":
        pickup_location = request.form.get("pickupLocation")
        dropoff_location = request.form.get("dropOffLocation")
        pickup_time = request.form.get("pickupTime")

        # Store data in the trips table
        with sqlite3.connect("trips.db") as con:
            cur = con.cursor()
            cur.execute("INSERT INTO trips (pickup_location, dropoff_location, pickup_time) VALUES (?, ?, ?)",
                        (pickup_location, dropoff_location, pickup_time))

    return render_template('destination.html')

@app.route('/process_destination', methods=['POST'])
def process_destination():
    pickup_location = request.form.get("pickupLocation")
    dropoff_location = request.form.get("dropOffLocation")
    pickup_time = request.form.get("pickupTime")

    # Process destination form data here
    # For now, let's just print the data
    print(f"Pickup Location: {pickup_location}")
    print(f"Drop-Off Location: {dropoff_location}")
    print(f"Pickup Time: {pickup_time}")

    return render_template('destination.html', pickup_location=pickup_location, dropoff_location=dropoff_location, pickup_time=pickup_time)

@socketio.on('send_message')
def handle_send_message_event(data):
    app.logger.info(f"{data['username']} has sent message: {data['message']}")
    socketio.emit('receive_message', data)

@app.route('/process_payment', methods=['POST'])
def process_payment():
    card_number = request.form.get('cardNumber')
    expiry_date = request.form.get('expiryDate')
    cvv = request.form.get('cvv')

    # Process payment form data here
    # For now, let's just print the data
    print(f"Card Number: {card_number}")
    print(f"Expiry Date: {expiry_date}")
    print(f"CVV: {cvv}")

    return "Payment processed successfully!"

@app.route('/chat')
def chat():
    return render_template('chat.html')

online_drivers = [
    {"id": 1, "name": "Driver A", "status": "online"},
    {"id": 2, "name": "Driver B", "status": "online"},
    # Add more drivers as needed
]

@app.route('/call_driver')
def call_driver():
    return render_template('call_driver.html')

@app.route('/get_driver_phone_number')
def get_driver_phone_number():
    # Example logic to fetch driver's phone number
    driver_phone_number = '1234567890'  # Replace with actual logic
    return jsonify({"phoneNumber": driver_phone_number})

if __name__ == '__main__':
    setup_sqlite()
    setup_sqlite_driver()
    setup_sqlite_trips()  
    socketio.run(app, debug=True)
