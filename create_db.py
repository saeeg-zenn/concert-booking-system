# This script creates our SQLite database and all its tables.
# We only need to run this ONCE (or whenever we want to reset the database from scratch).

import sqlite3

# This connects to a database file. If the file doesn't exist yet, SQLite creates it automatically.
connection = sqlite3.connect('database/database.db')

# A "cursor" is what we use to actually run SQL commands through Python.
cursor = connection.cursor()

# ---------- USERS TABLE ----------
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user'
    )
''')

# ---------- CONCERTS TABLE ----------
cursor.execute('''
    CREATE TABLE IF NOT EXISTS concerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        artist TEXT NOT NULL,
        concert_name TEXT NOT NULL,
        venue TEXT NOT NULL,
        city TEXT NOT NULL,
        date TEXT NOT NULL,
        time TEXT NOT NULL,
        price REAL NOT NULL,
        description TEXT,
        total_seats INTEGER NOT NULL
    )
''')

# ---------- SEATS TABLE ----------
cursor.execute('''
    CREATE TABLE IF NOT EXISTS seats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        concert_id INTEGER NOT NULL,
        seat_number TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'available',
        FOREIGN KEY (concert_id) REFERENCES concerts (id)
    )
''')

# ---------- BOOKINGS TABLE ----------
cursor.execute('''
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        concert_id INTEGER NOT NULL,
        booking_date TEXT NOT NULL,
        total_amount REAL NOT NULL,
        status TEXT NOT NULL DEFAULT 'confirmed',
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (concert_id) REFERENCES concerts (id)
    )
''')

# ---------- BOOKING_SEATS TABLE ----------
cursor.execute('''
    CREATE TABLE IF NOT EXISTS booking_seats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id INTEGER NOT NULL,
        seat_id INTEGER NOT NULL,
        FOREIGN KEY (booking_id) REFERENCES bookings (id),
        FOREIGN KEY (seat_id) REFERENCES seats (id)
    )
''')

# Save (permanently write) all these changes to the actual database file.
connection.commit()

# Always close the connection when you're done with it.
connection.close()

print("Database and tables created successfully!")