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

app = Flask(__name__, static_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), '../frontend')))
CORS(app)

@app.route('/')
def serve_index():
    # Debug Path
    frontend_dir = app.static_folder
    index_file = os.path.join(frontend_dir, 'index.html')
    
    if not os.path.exists(index_file):
        # List contents of directories to find where the file actually is
        try:
            root_files = os.listdir('/app')
        except:
            root_files = "Cannot read /app"
            
        try:
            cwd_files = os.listdir('.')
        except:
            cwd_files = "Cannot read ."
            
        return jsonify({
            "error": "index.html not found",
            "searched_at": index_file,
            "app_static_folder": app.static_folder,
            "files_in_root": root_files,
            "files_in_cwd": cwd_files
        })
        
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)

if __name__ == '__main__':
    if not os.path.exists(DB_PATH):
        asyncio.run(scrape_all())
        analyze_items()
    
    # Use PORT env var if available (for Cloud hosting)
    port = int(os.environ.get("PORT", 5001))
    print(f"Starting server on 0.0.0.0:{port}...")
    app.run(host='0.0.0.0', port=port)
