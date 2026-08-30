# This script creates 15 seats (A1-A5, B1-B5, C1-C5) for EACH concert in the database.

import sqlite3

connection = sqlite3.connect('database/database.db')
cursor = connection.cursor()

# First, find out which concerts actually exist, so we generate seats for the real ones.
cursor.execute("SELECT id FROM concerts")
concert_ids = cursor.fetchall()  # returns a list of tuples like [(1,), (2,), (3,)]

rows = ['A', 'B', 'C']
seats_per_row = 5

for (concert_id,) in concert_ids:  # unpacking each tuple to get just the id number
    for row_letter in rows:
        for seat_num in range(1, seats_per_row + 1):
            seat_number = f"{row_letter}{seat_num}"  # e.g. "A1", "B3", "C5"

            # For a bit of realism, mark seat B3 and C2 as already booked, on every concert.
            if seat_number in ["B3", "C2"]:
                status = "booked"
            else:
                status = "available"

            cursor.execute('''
                INSERT INTO seats (concert_id, seat_number, status)
                VALUES (?, ?, ?)
            ''', (concert_id, seat_number, status))

connection.commit()
connection.close()

print("Seats created successfully for all concerts!")