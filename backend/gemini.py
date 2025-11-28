import google.generativeai as genai
import os
import re
import requests
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv

# Load environment variables from the same directory or parent
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend', '.env'))

api_key = os.getenv("API_KEY")
if api_key:
    genai.configure(api_key=api_key)

MODEL_NAME = 'models/gemini-2.0-flash-lite'

def analyze_price_with_gemini(title, price, shipping=0, image_url=None):
    """
    Uses Gemini to estimate the fair market value of an item.
    """
    if not api_key:
        return {"error": "API Key not configured"}

    try:
        model = genai.GenerativeModel(model_name=MODEL_NAME)
        
        # Helper to get image data
        image_part = None
        if image_url:
            try:
                response = requests.get(image_url, timeout=5)
                if response.status_code == 200:
                    image = Image.open(BytesIO(response.content))
                    image_part = image
            except Exception as img_err:
                print(f"Image fetch error: {img_err}")

        prompt = f"""
        You are a professional appraiser of vintage goods.
        I need you to estimate the resale value of the following item on eBay/Etsy.
        
        Item: {title}
        Current Cost: ${price + shipping:.2f}
        
        Task:
        1. Identify if this is a desirable vintage item.
        2. Estimate a conservative resale price range.
        3. Provide a short reasoning (1 sentence).
        
        Response Format (JSON only):
        {{
            "estimated_value": 50.00,
            "reasoning": "Desirable mid-century brand, consistently sells for $40-60."
        }}
        """
        
        contents = [prompt]
        if image_part:
            contents.append(image_part)

        response = model.generate_content(contents)
        text = response.text.strip()
        
        # Extract JSON
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            import json
            return json.loads(match.group(0))
        else:
            return {"estimated_value": 0, "reasoning": "Could not parse AI response"}
            
    except Exception as e:
        print(f"Gemini Error: {e}")
        return {"estimated_value": 0, "reasoning": str(e)}

def batch_price_high_value_items(db_path, limit=20):
    """
    Automatically prices high-heuristic items that haven't been checked yet.
    """
    import sqlite3
    import time
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Select unpriced items with high heuristic score
    c.execute('''
        SELECT id, title, price, shipping, score, image_url 
        FROM items 
        WHERE score >= 30 
        AND gemini_price = 0 
        AND end_time > datetime('now')
        LIMIT ?
    ''', (limit,))
    
    items = c.fetchall()
    updates = []
    
    print(f"Batch Pricing: Found {len(items)} items to analyze...")
    
    for item in items:
        print(f"Analyzing: {item['title']}")
        result = analyze_price_with_gemini(item['title'], item['price'], item['shipping'], item['image_url'])
        
        if result.get('estimated_value'):
            updates.append((
                result['estimated_value'], 
                result['reasoning'], 
                item['id']
            ))
        
        # Modest sleep to avoid rate limits if necessary, though Gemini is usually fast
        time.sleep(1) 
        
    if updates:
        c.executemany('''
            UPDATE items 
            SET gemini_price = ?, gemini_analysis = ? 
            WHERE id = ?
        ''', updates)
        conn.commit()
        print(f"Batch Pricing: Updated {len(updates)} items.")
        
    conn.close()


