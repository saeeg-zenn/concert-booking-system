from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)
# TEMPORARY: this dictionary stands in for a real database, until Stage 4.
# Each key is a concert's ID number. Each value is a dictionary of that concert's info.
concerts_data = {
    1: {"artist": "Arijit Singh Live", "city": "Mumbai", "date": "12 Oct 2026", "price": 1500},
    2: {"artist": "Coldplay World Tour", "city": "Pune", "date": "5 Nov 2026", "price": 3000},
    3: {"artist": "Local Indie Night", "city": "Bangalore", "date": "20 Sep 2026", "price": 500},
}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/concerts')
def concerts():
    return render_template('concerts.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        print(f"Login attempt: {email} / {password}")  # shows up in your terminal, not the browser
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

@app.route('/booking')
def booking():
    return render_template('booking.html')

@app.route('/concert/<int:concert_id>')
def concert_details(concert_id):
    concert = concerts_data.get(concert_id)
    return f"You're viewing: {concert}"

if __name__ == '__main__':
    app.run(debug=True)