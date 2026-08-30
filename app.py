from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)


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
        print(f"Login attempt: {email} / {password}")
        return redirect(url_for('home'))

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        print(f"Registration attempt: {name} / {email} / {password}")
        return redirect(url_for('home'))

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


if __name__ == '__main__':
    app.run(debug=True)