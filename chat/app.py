from flask import Flask, render_template, request, redirect, url_for, session, flash
import psycopg2
import bcrypt
import uuid
import re
from datetime import datetime

app = Flask(__name__)
app.secret_key = "super_secret_key_for_session" # Change this for production

# --- AUTH LOGIC (Copied from authctl.py) ---
DB_URL = "postgres://postgres:password@localhost:5432/billing_engine"

def connect():
    return psycopg2.connect(DB_URL)

def validate_login(email, password):
    try:
        conn = connect()
        cur = conn.cursor()
        cur.execute("SELECT id, password_hash FROM users WHERE email=%s", (email,))
        row = cur.fetchone()
        conn.close()
        
        if row:
            user_id, stored_hash = row
            if bcrypt.checkpw(password.encode(), stored_hash.encode()):
                return user_id
    except Exception as e:
        print(f"Login Error: {e}")
    return None

def create_user_logic(email, password, tier_name):
    try:
        conn = connect()
        cur = conn.cursor()
        
        # Check if exists
        cur.execute("SELECT id FROM users WHERE email=%s", (email,))
        if cur.fetchone():
            return None

        # Get Tier
        cur.execute("SELECT id FROM tiers WHERE name = %s", (tier_name,))
        tier_row = cur.fetchone()
        if not tier_row: return None
        tier_id = tier_row[0]

        # Create
        user_id = str(uuid.uuid4())
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        
        cur.execute("INSERT INTO users(id, email, password_hash, created_at) VALUES (%s, %s, %s, %s)", 
                    (user_id, email, hashed, datetime.now()))
        cur.execute("INSERT INTO user_tiers(user_id, tier_id, created_at) VALUES (%s, %s, %s)", 
                    (user_id, tier_id, datetime.now()))
        
        # Create Default API Key
        key_val = str(uuid.uuid4())
        cur.execute("INSERT INTO api_keys(id, user_id, key_value, status, created_at) VALUES (%s, %s, %s, 'active', %s)",
                    (str(uuid.uuid4()), user_id, key_val, datetime.now()))

        conn.commit()
        conn.close()
        return user_id
    except Exception as e:
        print(f"Signup Error: {e}")
        return None

# --- ROUTES ---

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user_id = validate_login(email, password)
        
        if user_id:
            session['user_id'] = user_id
            session['email'] = email
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid Credentials")
            
    return render_template('auth.html', mode='login')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        tier = request.form.get('tier', 'free')
        
        user_id = create_user_logic(email, password, tier)
        if user_id:
            session['user_id'] = user_id
            session['email'] = email
            return redirect(url_for('dashboard'))
        else:
            flash("User already exists or Error")

    return render_template('auth.html', mode='signup')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # We pass the user_id to the HTML so JavaScript can use it
    return render_template('dashboard.html', user_id=session['user_id'], email=session['email'])

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    print("🚀 UI Server running on http://localhost:5000")

    app.run(port=5000, debug=True)
