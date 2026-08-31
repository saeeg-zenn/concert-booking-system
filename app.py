from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import datetime

app = Flask(__name__)

app.secret_key = 'dev-secret-key-change-this-later'


def get_db_connection():
    connection = sqlite3.connect('database/database.db')
    connection.row_factory = sqlite3.Row  # lets us access columns by name, not just by position
    return connection


@app.route('/')
def home():
    connection = get_db_connection()
    concerts = connection.execute('SELECT * FROM concerts').fetchall()
    connection.close()
    return render_template('index.html', concerts=concerts)


@app.route('/concerts')
def concerts():
    connection = get_db_connection()
    concerts = connection.execute('SELECT * FROM concerts').fetchall()
    connection.close()
    return render_template('concerts.html', concerts=concerts)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        connection = get_db_connection()
        user = connection.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        connection.close()

        if user is None:
            return "No account found with that email."  # temporary — we'll make this nicer in Stage 10

        if not check_password_hash(user['password'], password):
            return "Incorrect password."  # temporary — same, will be improved later

        # If we reach here, the email exists AND the password is correct.
        session['user_id'] = user['id']
        session['user_name'] = user['name']

        return redirect(url_for('home'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        connection = get_db_connection()

        # Check if this email is already registered, BEFORE trying to insert.
        existing_user = connection.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()

        if existing_user is not None:
            connection.close()
            return "An account with that email already exists."  # temporary message, improved in Stage 10

        hashed_password = generate_password_hash(password)

        connection.execute(
            'INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)',
            (name, email, hashed_password, 'user')
        )
        connection.commit()
        connection.close()

        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/booking/<int:concert_id>')
def booking(concert_id):
    connection = get_db_connection()
    concert = connection.execute('SELECT * FROM concerts WHERE id = ?', (concert_id,)).fetchone()
    seats = connection.execute('SELECT * FROM seats WHERE concert_id = ?', (concert_id,)).fetchall()
    connection.close()

    # Split seats into 3 rows based on their seat_number's first letter.
    # This is plain Python, so we don't need to rely on any special Jinja features.
    row_a = [seat for seat in seats if seat['seat_number'].startswith('A')]
    row_b = [seat for seat in seats if seat['seat_number'].startswith('B')]
    row_c = [seat for seat in seats if seat['seat_number'].startswith('C')]

    return render_template('booking.html', concert=concert, row_a=row_a, row_b=row_b, row_c=row_c)


@app.route('/concert/<int:concert_id>')
def concert_details(concert_id):
    connection = get_db_connection()
    concert = connection.execute('SELECT * FROM concerts WHERE id = ?', (concert_id,)).fetchone()
    connection.close()
    return render_template('concert-details.html', concert=concert)


@app.route('/book-seats', methods=['POST'])
def book_seats():
    # Step 1: make sure the user is actually logged in.
    if 'user_id' not in session:
        return jsonify(success=False, message="You must be logged in to book seats."), 401

    data = request.get_json()  # reads the JSON body sent by fetch()
    concert_id = data.get('concert_id')
    seat_ids = data.get('seat_ids')

    if not seat_ids:
        return jsonify(success=False, message="No seats were selected."), 400

    connection = get_db_connection()

    # Step 2: get the concert's REAL price from the database — never trust a price from the browser.
    concert = connection.execute('SELECT * FROM concerts WHERE id = ?', (concert_id,)).fetchone()
    if concert is None:
        connection.close()
        return jsonify(success=False, message="Concert not found."), 404

    # Step 3: re-check EVERY selected seat is still actually available right now.
    placeholders = ','.join('?' for _ in seat_ids)  # builds "?,?,?" to match however many seat_ids we got
    seats = connection.execute(
        f'SELECT * FROM seats WHERE id IN ({placeholders}) AND concert_id = ?',
        (*seat_ids, concert_id)
    ).fetchall()

    if len(seats) != len(seat_ids):
        connection.close()
        return jsonify(success=False, message="One or more selected seats don't exist for this concert."), 400

    for seat in seats:
        if seat['status'] == 'booked':
            connection.close()
            return jsonify(success=False, message=f"Seat {seat['seat_number']} was just booked by someone else. Please choose another seat."), 409

    # Step 4: calculate the REAL total, using the database price, not anything from the browser.
    total_amount = concert['price'] * len(seat_ids)

    # Step 5: create the booking record.
    booking_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor = connection.execute(
        'INSERT INTO bookings (user_id, concert_id, booking_date, total_amount, status) VALUES (?, ?, ?, ?, ?)',
        (session['user_id'], concert_id, booking_date, total_amount, 'confirmed')
    )
    booking_id = cursor.lastrowid  # the ID SQLite just auto-assigned to this new booking

    # Step 6 & 7: link each seat to this booking, and mark it as booked.
    for seat_id in seat_ids:
        connection.execute(
            'INSERT INTO booking_seats (booking_id, seat_id) VALUES (?, ?)',
            (booking_id, seat_id)
        )
        connection.execute(
            'UPDATE seats SET status = ? WHERE id = ?',
            ('booked', seat_id)
        )

    connection.commit()
    connection.close()

    return jsonify(success=True, booking_id=booking_id)

@app.route('/my-bookings')
def my_bookings():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    connection = get_db_connection()

    bookings = connection.execute('''
        SELECT bookings.id AS booking_id,
               bookings.booking_date,
               bookings.total_amount,
               bookings.status,
               concerts.concert_name,
               concerts.artist,
               concerts.city,
               concerts.date AS concert_date
        FROM bookings
        JOIN concerts ON bookings.concert_id = concerts.id
        WHERE bookings.user_id = ?
        ORDER BY bookings.booking_date DESC
    ''', (session['user_id'],)).fetchall()

    connection.close()
    return render_template('my-bookings.html', bookings=bookings)

if __name__ == '__main__':
    app.run(debug=True)