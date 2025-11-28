from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import sqlite3
import os
import asyncio
import threading
import schedule
import time
import json
from datetime import datetime
from scraper import scrape_all
from analyzer import analyze_items
from gemini import analyze_price_with_gemini, batch_price_high_value_items

# Explicitly disable static folder magic to prevent conflicts
app = Flask(__name__, static_folder=None)
CORS(app)

# Define paths manually
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Frontend is one level up from backend
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, '../frontend'))
DB_PATH = os.path.join(BASE_DIR, 'gw_data.db')
SELLER_MAP_PATH = os.path.join(BASE_DIR, 'seller_map.json')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_sellers():
    try:
        with open(SELLER_MAP_PATH, 'r') as f:
            return json.load(f)
    except:
        return {}

# --- Scheduler ---
def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(60)

def daily_job():
    print("Running Daily Scrape...")
    asyncio.run(scrape_all())
    analyze_items()
    batch_price_high_value_items(DB_PATH, limit=50)

# Schedule daily at 8 AM
schedule.every().day.at("08:00").do(daily_job)
threading.Thread(target=run_schedule, daemon=True).start()

# --- API Endpoints ---

@app.route('/api/refresh', methods=['POST'])
def refresh_data():
    """Triggers a fresh scrape and analysis."""
    def run_pipeline():
        asyncio.run(scrape_all())
        analyze_items()
        batch_price_high_value_items(DB_PATH, limit=20)
        
    thread = threading.Thread(target=run_pipeline)
    thread.start()
    return jsonify({"status": "started", "message": "Scraping & AI Analysis in background..."})

@app.route('/api/items', methods=['GET'])
def get_items():
    """Search and Filter Items."""
    search = request.args.get('search', '')
    seller_id = request.args.get('seller_id', '')
    min_score = request.args.get('min_score', 0, type=int)
    sort = request.args.get('sort', 'score') # score, time, price
    
    # Filter expired items
    query = "SELECT * FROM items WHERE end_time > ?"
    params = [datetime.now().isoformat()]
    
    if search:
        query += " AND title LIKE ?"
        params.append(f"%{search}%")
        
    if seller_id:
        query += " AND seller_id = ?"
        params.append(seller_id)
        
    if min_score > 0:
        query += " AND score >= ?"
        params.append(min_score)
        
    # Sorting - Prioritize Profit
    if sort == 'time':
        query += " ORDER BY end_time ASC"
    elif sort == 'price':
        query += " ORDER BY price ASC"
    else:
        # Custom Sort: 
        # 1. AI Verified Profit (Gemini Price - Cost) DESC
        # 2. High Heuristic Score DESC
        query += '''
            ORDER BY 
            CASE WHEN gemini_price > 0 THEN (gemini_price - price - shipping) ELSE -1000 END DESC, 
            score DESC, 
            end_time ASC
        '''
        
    query += " LIMIT 200"
    
    conn = get_db_connection()
    items = conn.execute(query, params).fetchall()
    conn.close()
    return jsonify([dict(ix) for ix in items])

@app.route('/api/saved', methods=['GET'])
def get_saved_items():
    conn = get_db_connection()
    items = conn.execute("SELECT * FROM items WHERE is_saved = 1 ORDER BY end_time ASC").fetchall()
    conn.close()
    return jsonify([dict(ix) for ix in items])

@app.route('/api/items/<id>/save', methods=['POST'])
def toggle_save(id):
    conn = get_db_connection()
    # Toggle
    current = conn.execute("SELECT is_saved FROM items WHERE id = ?", (id,)).fetchone()
    if current:
        new_status = 0 if current['is_saved'] else 1
        conn.execute("UPDATE items SET is_saved = ? WHERE id = ?", (new_status, id))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "is_saved": new_status})
    conn.close()
    return jsonify({"error": "Item not found"}), 404

@app.route('/api/items/<id>/analyze', methods=['POST'])
def run_gemini_analysis(id):
    conn = get_db_connection()
    item = conn.execute("SELECT * FROM items WHERE id = ?", (id,)).fetchone()
    
    if not item:
        conn.close()
        return jsonify({"error": "Item not found"}), 404
        
    # Run Analysis
    result = analyze_price_with_gemini(item['title'], item['price'], item['shipping'], item['image_url'])
    
    if result.get('estimated_value'):
        conn.execute('''
            UPDATE items 
            SET gemini_price = ?, gemini_analysis = ? 
            WHERE id = ?
        ''', (result['estimated_value'], result['reasoning'], id))
        conn.commit()
    
    conn.close()
    return jsonify(result)

@app.route('/api/sellers', methods=['GET'])
def get_sellers_list():
    return jsonify(get_sellers())

@app.route('/')
def serve_index():
    index_path = os.path.join(FRONTEND_DIR, 'index.html')
    if not os.path.exists(index_path):
        return jsonify({
            "error": "File not found",
            "path": index_path,
            "cwd": os.getcwd(),
            "contents": os.listdir(os.getcwd()) if os.path.exists(os.getcwd()) else "No CWD"
        }), 404
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(FRONTEND_DIR, path)

if __name__ == '__main__':
    if not os.path.exists(DB_PATH):
        asyncio.run(scrape_all())
        analyze_items()
    
    # Use PORT env var if available (for Cloud hosting)
    port = int(os.environ.get("PORT", 5001))
    print(f"Starting server on 0.0.0.0:{port}...")
    app.run(host='0.0.0.0', port=port)
