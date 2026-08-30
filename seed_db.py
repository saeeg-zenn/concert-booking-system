# This script inserts sample concert data into our database.
# "Seeding" a database means filling it with initial/sample data to work with.

import sqlite3

connection = sqlite3.connect('database/database.db')
cursor = connection.cursor()

# A list of concerts to insert. Each one is a tuple of values,
# matching the column order in our CREATE TABLE statement:
# artist, concert_name, venue, city, date, time, price, description, total_seats
concerts = [
    ("Arijit Singh", "Arijit Singh Live", "DY Patil Stadium", "Mumbai", "2026-10-12", "19:00", 1500, "An evening of soulful Bollywood hits.", 15),
    ("Coldplay", "Coldplay World Tour", "Balewadi Stadium", "Pune", "2026-11-05", "18:30", 3000, "Coldplay brings their spectacular world tour to India.", 15),
    ("Various Artists", "Local Indie Night", "The Humming Tree", "Bangalore", "2026-09-20", "20:00", 500, "A night celebrating Bangalore's indie music scene.", 15),
]

# executemany() runs the same INSERT command once for each tuple in our list — efficient for bulk inserts.
cursor.executemany('''
    INSERT INTO concerts (artist, concert_name, venue, city, date, time, price, description, total_seats)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
''', concerts)

connection.commit()
connection.close()

print(f"Inserted {len(concerts)} concerts successfully!")