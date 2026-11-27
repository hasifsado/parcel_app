from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import random
import string
import os

app = Flask(__name__)

# --- DATABASE SETUP ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'parcel.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS parcels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tracking_number TEXT UNIQUE NOT NULL,
            seller_id INTEGER NOT NULL,
            recipient_name TEXT NOT NULL,
            recipient_phone TEXT NOT NULL,
            recipient_address TEXT NOT NULL,
            weight REAL NOT NULL,
            current_status TEXT DEFAULT 'Registered',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS status_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parcel_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (parcel_id) REFERENCES parcels(id)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- HELPER FUNCTIONS ---
def generate_tracking_number():
    while True:
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))
        tracking_num = f"TRK-{random_str}"
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM parcels WHERE tracking_number = ?", (tracking_num,))
        exists = cursor.fetchone()
        conn.close()
        
        if not exists:
            return tracking_num

# --- ROUTES ---
@app.route('/')
def home():
    return "<h1>Welcome to the Parcel System</h1><a href='/register'>Go to Register Parcel</a><br><a href='/track'>Go to Public Tracking</a>"

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        address = request.form['address']
        weight = request.form['weight']
        
        tracking_number = generate_tracking_number()
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO parcels (tracking_number, seller_id, recipient_name, recipient_phone, recipient_address, weight)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (tracking_number, 1, name, phone, address, weight))
        
        parcel_id = cursor.lastrowid
        
        cursor.execute('''
            INSERT INTO status_history (parcel_id, status)
            VALUES (?, 'Registered')
        ''', (parcel_id,))
        
        conn.commit()
        conn.close()
        
        return f"<h2>Success!</h2><p>Parcel registered. Tracking Number: <b>{tracking_number}</b></p><a href='/register'>Register another</a>"
    
    return render_template('register.html')

# --- PUBLIC TRACKING ROUTES ---
@app.route('/track', methods=['GET'])
def track_page():
    return render_template('track.html')

@app.route('/track/<tracking_number>', methods=['GET'])
def track_result(tracking_number):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, current_status FROM parcels WHERE tracking_number = ?", (tracking_number,))
    parcel = cursor.fetchone()
    
    if not parcel:
        conn.close()
        return render_template('track.html', error="Tracking number not found.")
    
    parcel_id = parcel[0]
    
    cursor.execute('''
        SELECT status, updated_at 
        FROM status_history 
        WHERE parcel_id = ? 
        ORDER BY updated_at ASC
    ''', (parcel_id,))
    
    history = cursor.fetchall()
    conn.close()
    
    return render_template('track.html', tracking_number=tracking_number, history=history)
@app.route('/my-parcels', methods=['GET'])
def my_parcels():
    # In the future, this will be the logged-in user's ID from Module 1
    current_seller_id = 1 
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Search filter (if the user typed something in the search bar)
    search_query = request.args.get('search', '')
    
    if search_query:
        # Search by tracking number OR recipient name
        cursor.execute('''
            SELECT tracking_number, recipient_name, current_status, created_at 
            FROM parcels 
            WHERE seller_id = ? AND (tracking_number LIKE ? OR recipient_name LIKE ?)
            ORDER BY created_at DESC
        ''', (current_seller_id, f'%{search_query}%', f'%{search_query}%'))
    else:
        # Show all parcels for this seller
        cursor.execute('''
            SELECT tracking_number, recipient_name, current_status, created_at 
            FROM parcels 
            WHERE seller_id = ?
            ORDER BY created_at DESC
        ''', (current_seller_id,))
        
    parcels = cursor.fetchall()
    conn.close()
    
    return render_template('my_parcels.html', parcels=parcels, search_query=search_query)
if __name__ == '__main__':
    app.run(debug=True)