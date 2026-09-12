from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3
import datetime

app = Flask(__name__)

app.secret_key = 'dev-secret-key-change-this-later'


def get_db_connection():
    connection = sqlite3.connect('database/database.db')
    connection.row_factory = sqlite3.Row  # lets us access columns by name, not just by position
    return connection


def is_admin():
    return session.get('user_role') == 'admin'


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if not is_admin():
            return "You do not have permission to access this page.", 403
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
def home():
    connection = get_db_connection()
    concerts = connection.execute('SELECT * FROM concerts').fetchall()
    connection.close()
    return render_template('index.html', concerts=concerts)


@app.route('/concerts')
def concerts():
    # Read optional search/filter values from the URL's query string.
    # If any of these weren't provided, default to an empty string.
    search_query = request.args.get('search', '')
    city_filter = request.args.get('city', '')
    date_filter = request.args.get('date', '')

    # Build the SQL query dynamically, piece by piece, based on what filters were given.
    sql = 'SELECT * FROM concerts WHERE 1=1'
    params = []

    if search_query:
        sql += ' AND (concert_name LIKE ? OR artist LIKE ?)'
        params.append(f'%{search_query}%')
        params.append(f'%{search_query}%')

    if city_filter:
        sql += ' AND city = ?'
        params.append(city_filter)

    if date_filter:
        sql += ' AND date = ?'
        params.append(date_filter)

    connection = get_db_connection()
    concerts = connection.execute(sql, params).fetchall()

    # Also get a list of distinct cities, to populate the city dropdown dynamically.
    cities = connection.execute('SELECT DISTINCT city FROM concerts ORDER BY city').fetchall()

    connection.close()

    return render_template('concerts.html', concerts=concerts, cities=cities,
                            search_query=search_query, city_filter=city_filter, date_filter=date_filter)
    

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        connection = get_db_connection()
        user = connection.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        connection.close()

        if user is None:
            flash("No account found with that email.", "error")
            return redirect(url_for('login'))

        if not check_password_hash(user['password'], password):
            flash("Incorrect password.", "error")
            return redirect(url_for('login'))

        # If we reach here, the email exists AND the password is correct.
        session['user_id'] = user['id']
        session['user_name'] = user['name']
        session['user_role'] = user['role']

        flash(f"Welcome back, {user['name']}!", "success")
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
            flash("An account with that email already exists.", "error")
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)

        connection.execute(
            'INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)',
            (name, email, hashed_password, 'user')
        )
        connection.commit()
        connection.close()

        flash("Account created successfully! Please log in.", "success")
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


@app.route('/cancel-booking/<int:booking_id>', methods=['POST'])
def cancel_booking(booking_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    connection = get_db_connection()

    # Step 1: find this booking, and confirm it actually belongs to the logged-in user.
    booking = connection.execute(
        'SELECT * FROM bookings WHERE id = ? AND user_id = ?',
        (booking_id, session['user_id'])
    ).fetchone()

    if booking is None:
        connection.close()
        flash("Booking not found, or you don't have permission to cancel it.", "error")
        return redirect(url_for('my_bookings'))

    if booking['status'] == 'cancelled':
        connection.close()
        return redirect(url_for('my_bookings'))  # already cancelled, nothing to do

    # Step 2: find every seat linked to this booking, and set each one back to 'available'.
    seat_links = connection.execute(
        'SELECT seat_id FROM booking_seats WHERE booking_id = ?',
        (booking_id,)
    ).fetchall()

    for link in seat_links:
        connection.execute(
            'UPDATE seats SET status = ? WHERE id = ?',
            ('available', link['seat_id'])
        )

    # Step 3: mark the booking itself as cancelled (we keep the record, not delete it).
    connection.execute(
        'UPDATE bookings SET status = ? WHERE id = ?',
        ('cancelled', booking_id)
    )

    connection.commit()
    connection.close()

    flash("Booking cancelled successfully.", "success")
    return redirect(url_for('my_bookings'))


@app.route('/admin')
@admin_required
def admin_dashboard():
    connection = get_db_connection()

    total_concerts = connection.execute('SELECT COUNT(*) FROM concerts').fetchone()[0]
    total_users = connection.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    total_bookings = connection.execute("SELECT COUNT(*) FROM bookings WHERE status = 'confirmed'").fetchone()[0]
    all_concerts = connection.execute('SELECT * FROM concerts ORDER BY id DESC').fetchall()

    connection.close()

    return render_template('admin.html',
                            total_concerts=total_concerts,
                            total_users=total_users,
                            total_bookings=total_bookings,
                            all_concerts=all_concerts)


@app.route('/admin/concerts/add', methods=['GET', 'POST'])
@admin_required
def add_concert():
    if request.method == 'POST':
        artist = request.form['artist']
        concert_name = request.form['concert_name']
        venue = request.form['venue']
        city = request.form['city']
        date = request.form['date']
        time = request.form['time']
        price = request.form['price']
        description = request.form['description']
        total_seats = request.form['total_seats']

        connection = get_db_connection()
        cursor = connection.execute('''
            INSERT INTO concerts (artist, concert_name, venue, city, date, time, price, description, total_seats)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (artist, concert_name, venue, city, date, time, price, description, total_seats))

        new_concert_id = cursor.lastrowid

        # Automatically generate the seat map for this new concert too,
        # same pattern as seed_seats.py from Stage 4.
        rows = ['A', 'B', 'C']
        for row_letter in rows:
            for seat_num in range(1, 6):
                seat_number = f"{row_letter}{seat_num}"
                connection.execute(
                    'INSERT INTO seats (concert_id, seat_number, status) VALUES (?, ?, ?)',
                    (new_concert_id, seat_number, 'available')
                )

        connection.commit()
        connection.close()

        flash("Concert added successfully.", "success")
        return redirect(url_for('admin_dashboard'))

    return render_template('admin-add-concert.html')


@app.route('/admin/concerts/edit/<int:concert_id>', methods=['GET', 'POST'])
@admin_required
def edit_concert(concert_id):
    connection = get_db_connection()

    if request.method == 'POST':
        artist = request.form['artist']
        concert_name = request.form['concert_name']
        venue = request.form['venue']
        city = request.form['city']
        date = request.form['date']
        time = request.form['time']
        price = request.form['price']
        description = request.form['description']

        connection.execute('''
            UPDATE concerts
            SET artist = ?, concert_name = ?, venue = ?, city = ?, date = ?, time = ?, price = ?, description = ?
            WHERE id = ?
        ''', (artist, concert_name, venue, city, date, time, price, description, concert_id))

        connection.commit()
        connection.close()

        flash("Concert updated successfully.", "success")
        return redirect(url_for('admin_dashboard'))

    concert = connection.execute('SELECT * FROM concerts WHERE id = ?', (concert_id,)).fetchone()
    connection.close()

    if concert is None:
        return "Concert not found.", 404

    return render_template('admin-edit-concert.html', concert=concert)


@app.route('/admin/concerts/delete/<int:concert_id>', methods=['POST'])
@admin_required
def delete_concert(concert_id):
    connection = get_db_connection()

    existing_bookings = connection.execute(
        'SELECT COUNT(*) FROM bookings WHERE concert_id = ?', (concert_id,)
    ).fetchone()[0]

    if existing_bookings > 0:
        connection.close()
        flash("Cannot delete a concert that has existing bookings.", "error")
        return redirect(url_for('admin_dashboard'))

    connection.execute('DELETE FROM seats WHERE concert_id = ?', (concert_id,))
    connection.execute('DELETE FROM concerts WHERE id = ?', (concert_id,))
    connection.commit()
    connection.close()

    flash("Concert deleted successfully.", "success")
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/users')
@admin_required
def admin_users():
    connection = get_db_connection()
    users = connection.execute('SELECT id, name, email, role FROM users ORDER BY id').fetchall()
    connection.close()
    return render_template('admin-users.html', users=users)


@app.route('/admin/bookings')
@admin_required
def admin_bookings():
    connection = get_db_connection()
    bookings = connection.execute('''
        SELECT bookings.id AS booking_id,
               bookings.booking_date,
               bookings.total_amount,
               bookings.status,
               users.name AS user_name,
               users.email AS user_email,
               concerts.concert_name
        FROM bookings
        JOIN users ON bookings.user_id = users.id
        JOIN concerts ON bookings.concert_id = concerts.id
        ORDER BY bookings.booking_date DESC
    ''').fetchall()
    connection.close()
    return render_template('admin-bookings.html', bookings=bookings)


if __name__ == '__main__':
    app.run(debug=True)