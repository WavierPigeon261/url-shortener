import string
import random
import sqlite3
import os
from flask import Flask, request, redirect, jsonify, render_template

app = Flask(__name__)

# Render wipes the server on restarts. Saving to /data keeps it permanent
# if we attach a persistent disk. For local testing, it falls back to 'urls.db'
if os.path.exists('/data'):
    DB_FILE = '/data/urls.db'
else:
    DB_FILE = 'urls.db'

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS urls (
                short_id TEXT PRIMARY KEY,
                long_url TEXT NOT NULL
            )
        ''')
        conn.commit()

# CRITICAL FIX: Run this here so Gunicorn executes it on Render
init_db()

def generate_short_id(length=6):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

@app.route('/')
def home():
    """Serves the visual HTML web page to the user."""
    return render_template('index.html')

@app.route('/shorten', methods=['POST'])
def shorten_url():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({"error": "Missing 'url' parameter"}), 400
    
    long_url = data['url']
    if not long_url.startswith(('http://', 'https://')):
        long_url = 'https://' + long_url

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        while True:
            short_id = generate_short_id()
            cursor.execute('SELECT 1 FROM urls WHERE short_id = ?', (short_id,))
            if not cursor.fetchone():
                break

        cursor.execute('INSERT INTO urls (short_id, long_url) VALUES (?, ?)', (short_id, long_url))
        conn.commit()

    domain = request.host_url
    return jsonify({
        "long_url": long_url,
        "short_url": f"{domain}{short_id}"
    })

@app.route('/<short_id>')
def redirect_to_url(short_id):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT long_url FROM urls WHERE short_id = ?', (short_id,))
        row = cursor.fetchone()
        
    if row:
        return redirect(row[0])
    return "URL not found", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
