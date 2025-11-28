import aiohttp
import asyncio
import json
import os
import sqlite3
from datetime import datetime

# Load configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'gw_data.db')
SELLER_MAP_PATH = os.path.join(BASE_DIR, 'seller_map.json')
CATEGORY_IDS_PATH = os.path.join(BASE_DIR, 'category_ids.json')

API_URL = "https://buyerapi.shopgoodwill.com/api/Search/ItemListing"

HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Origin": "https://shopgoodwill.com",
    "Referer": "https://shopgoodwill.com/"
}

async def fetch_page(session, page=1, category_id=0):
    payload = {
        "catIds": "",
        "categoryId": category_id,
        "categoryLevel": 1,
        "categoryLevelNo": "1",
        "closedAuctionDaysBack": "7",
        "closedAuctionEndingDate": datetime.now().strftime("%m/%d/%Y"),
        "highPrice": "999999",
        "isFromHeaderMenuTab": False,
        "isFromHomePage": False,
        "isMultipleCategoryIds": False,
        "isSize": False,
        "isWeddingCatagory": "false",
        "layout": "",
        "lowPrice": "0",
        "page": str(page),
        "pageSize": "40",
        "partNumber": "",
        "savedSearchId": 0,
        "searchBuyNowOnly": "",
        "searchCanadaShipping": "false",
        "searchClosedAuctions": "false",
        "searchDescriptions": "false",
        "searchInternationalShippingOnly": "false",
        "searchNoPickupOnly": "false",
        "searchOneCentShippingOnly": "false",
        "searchPickupOnly": "false",
        "searchText": "",
        "searchUSOnlyShipping": "true",
        "selectedCategoryIds": "",
        "selectedGroup": "",
        "selectedSellerIds": "", # Empty means ALL sellers
        "sortColumn": "1",
        "sortDescending": "false",
        "useBuyerPrefs": "true"
    }
    
    try:
        async with session.post(API_URL, json=payload, headers=HEADERS, timeout=15) as response:
            if response.status == 200:
                return await response.json()
            else:
                print(f"Error fetching page {page}: {response.status}")
                return None
    except Exception as e:
        print(f"Exception on page {page}: {str(e)}")
        return None

async def scrape_all():
    """
    Main scraping function. 
    Since scraping EVERYTHING (150k+ items) takes time, we will:
    1. Scrape the first X pages of 'All' to get ending soonest items (Sort 1 = Ending Soon).
    2. Or iterate through categories if we want deep coverage.
    
    Strategy: Get the first 50 pages (2000 items) ending soonest. These are the actionable money makers.
    """
    print("Starting scrape job...")
    
    # Initialize DB
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Optimization: WAL mode for better concurrency
    c.execute('PRAGMA journal_mode=WAL;')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id TEXT PRIMARY KEY,
            title TEXT,
            price REAL,
            shipping REAL,
            bids INTEGER,
            end_time TEXT,
            image_url TEXT,
            seller_id TEXT,
            category_id TEXT,
            scraped_at TEXT,
            score INTEGER DEFAULT 0,
            is_saved BOOLEAN DEFAULT 0,
            gemini_price REAL DEFAULT 0,
            gemini_analysis TEXT
        )
    ''')
    conn.commit()
    
    items_buffer = []
    MAX_PAGES = 150 # ~6000 items
    CHUNK_SIZE = 25 # Commit every 25 pages (1000 items)
    
    async with aiohttp.ClientSession() as session:
        for i in range(0, MAX_PAGES, CHUNK_SIZE):
            tasks = []
            start_page = i + 1
            end_page = min(i + CHUNK_SIZE, MAX_PAGES)
            
            print(f"Fetching pages {start_page} to {end_page}...")
            
            for p in range(start_page, end_page + 1):
                tasks.append(fetch_page(session, page=p))
                
            results = await asyncio.gather(*tasks)
            
            batch_items = []
            for data in results:
                if data and 'searchResults' in data and 'items' in data['searchResults']:
                    for item in data['searchResults']['items']:
                        try:
                            record = (
                                str(item.get('itemId')),
                                item.get('title', ''),
                                float(item.get('currentPrice', 0)),
                                float(item.get('shippingPrice', 0)),
                                int(item.get('numBids', 0)),
                                item.get('endTime', ''),
                                item.get('imageURL', ''),
                                str(item.get('sellerId', '')),
                                str(item.get('categoryId', '')),
                                datetime.now().isoformat()
                            )
                            batch_items.append(record)
                        except Exception as e:
                            continue
            
            if batch_items:
                c.executemany('''
                    INSERT INTO items 
                    (id, title, price, shipping, bids, end_time, image_url, seller_id, category_id, scraped_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        title=excluded.title,
                        price=excluded.price,
                        shipping=excluded.shipping,
                        bids=excluded.bids,
                        end_time=excluded.end_time,
                        image_url=excluded.image_url,
                        seller_id=excluded.seller_id,
                        category_id=excluded.category_id,
                        scraped_at=excluded.scraped_at
                ''', batch_items)
                conn.commit()
                items_buffer.extend(batch_items)
                print(f"Committed batch of {len(batch_items)} items.")
            
            # Prevent rate limiting
            await asyncio.sleep(0.5)

    print(f"Successfully scraped and stored {len(items_buffer)} items total.")
        
    conn.close()
    return len(items_buffer)

if __name__ == "__main__":
    asyncio.run(scrape_all())

