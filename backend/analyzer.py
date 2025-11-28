import sqlite3
import re
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'gw_data.db')

# Regex Patterns for Valuation - VINTAGE / ART / HOME GOODS FOCUS
HIGH_VALUE_PATTERNS = {
    # Jewelry / Metals (EXCLUDED per user request, but keeping Sterling/Gold for flatware/decor)
    # r'\b14k\b': 50,
    # r'\b18k\b': 60,
    # r'\b925\b': 20,
    r'\bsterling\b': 25, # Often flatware/holloware
    r'\bgold\b': 15,     # Often decor
    # r'\bplatinum\b': 40,
    # r'\brolex\b': 100,
    # r'\bomega\b': 50,
    # r'\bcartier\b': 50,
    # r'\btiffany\b': 40, # Tiffany lamps/glass are good, but often jewelry.
    # r'\bdiamond\b': 15,
    # r'\bgemstone\b': 10,
    # r'\byurman\b': 30,
    # r'\bhardy\b': 30,

    # Vintage / Art
    r'\bmid century\b': 30,
    r'\bmcm\b': 30,
    r'\bart deco\b': 25,
    r'\bart nouveau\b': 25,
    r'\bvintage\b': 10,
    r'\bantique\b': 15,
    r'\bsigned\b': 20,
    r'\boil painting\b': 30,
    r'\blithograph\b': 20,
    r'\betching\b': 20,
    r'\bwoodblock\b': 20,
    r'\bbronze\b': 30,
    r'\bsculpture\b': 25,
    r'\bstudio pottery\b': 20,
    r'\bvase\b': 10,
    r'\bmurano\b': 25,
    r'\bwaterford\b': 20,
    r'\bbaccarat\b': 30,
    r'\blalique\b': 30,
    r'\blladro\b': 20,
    r'\bswarovski\b': 15,

    # High-End Kitchen / Home
    r'\ble creuset\b': 35,
    r'\bstaub\b': 35,
    r'\bmauviel\b': 40,
    r'\bcopper\b': 20, # Boosted
    r'\bpyrex\b': 20,
    r'\bfiestaware\b': 15,
    r'\bdansk\b': 20,
    r'\bcathrineholm\b': 40,
    r'\bherman miller\b': 50,
    r'\bknoll\b': 40,
    r'\beames\b': 50,
    r'\bpendleton\b': 35, # Boosted for blankets
    r'\bwool\b': 15,
    r'\bblanket\b': 15,
    r'\bcashmere\b': 15,
    r'\bsilk\b': 10,
    r'\bpersian\b': 30,
    r'\brug\b': 15,
    r'\bfurniture\b': 20,
    r'\bchair\b': 15,
    r'\barmchair\b': 20,
    r'\bsofa\b': 25,
    r'\bwood\b': 10,
    r'\bcarved\b': 15,
    r'\bbrass\b': 20,
    r'\bporcelain\b': 15,
    r'\bblue.*white\b': 20, # Blue and White decor
    r'\btransferware\b': 20,
    r'\bspode\b': 20,
    r'\bstaffordshire\b': 20,
    
    # Children / Toys (NEW FOCUS)
    r'\bsteiff\b': 40,
    r'\bcarhartt\b': 40, # Kids Carhartt
    r'\boshkosh\b': 25,
    r'\boveralls\b': 20,
    r'\bdenim\b': 15,
    r'\blevi\b': 15,
    r'\bvintage.*child\b': 25,
    r'\bvintage.*toy\b': 25,
    r'\bwood.*toy\b': 20,
    r'\bwooden.*toy\b': 20,
    r'\bwicker\b': 25,
    r'\brattan\b': 25,
    r'\bdollhouse\b': 25,
    r'\bminiature\b': 15,
    r'\bmontessori\b': 20,
    r'\bbrio\b': 20,
    r'\bmaileg\b': 30,
    r'\bamerican girl\b': 20,
    r'\bpolly pocket\b': 20,
    
    # Art Refinements
    r'\bframed\b': 10,
    r'\blandscape\b': 20,
    r'\bseascape\b': 20,
    r'\bportrait\b': 20,
    r'\bcanvas\b': 15,
    r'\boriginal art\b': 25,

    # Vintage Fashion / Leather
    r'\bhermes\b': 50,
    r'\bvuitton\b': 30,
    r'\bchanel\b': 30,
    r'\bgucci\b': 30,
    r'\bfendi\b': 25,
    r'\bdooney\b': 15, # Vintage Dooney is solid
    r'\bcoach\b': 10,
}

# Explicitly filtering out Electronics and Junk
NEGATIVE_PATTERNS = [
    # Jewelry Exclusion
    r'\bnecklace\b',
    r'\bring\b',
    r'\bearring\b',
    r'\bearrings\b',
    r'\bbracelet\b',
    r'\bbracelets\b',
    r'\bjewelry\b',
    r'\bpendant\b',
    r'\bcharm\b',
    r'\brooch\b',
    r'\bwatch\b',
    r'\bwristwatch\b',
    r'\b14k\b', 
    r'\b18k\b',
    r'\b10k\b', 
    r'\b925\b', # Usually jewelry if not specified as flatware

    # Condition
    r'\bbroken\b',
    r'\bparts\b',
    r'\bdamaged\b',
    r'\brepair\b',
    r'\bas-is\b',
    r'\bempty box\b',
    r'\bfor parts\b',
    r'\buntested\b',
    
    # Electronics (Strictly Excluded)
    r'\bsony\b',
    r'\bnintendo\b',
    r'\bxbox\b',
    r'\bplaystation\b',
    r'\bps[1-5]\b',
    r'\bdell\b',
    r'\bhp\b',
    r'\blaptop\b',
    r'\bcomputer\b',
    r'\bmonitor\b',
    r'\bkeyboard\b',
    r'\bmouse\b',
    r'\bprinter\b',
    r'\bdvd\b',
    r'\bvhs\b',
    r'\breceiver\b',
    r'\bspeaker\b',
    r'\bwii\b',
    r'\bipod\b',
    r'\bipad\b',
    r'\biphone\b',
    r'\bmacbook\b',
    r'\btablet\b',
    r'\bkindle\b',
    r'\bfitbit\b',
    r'\bcamera\b', # Generally exclude unless user specifies vintage cameras allowed, but user said NO electronics.
    r'\bdigital\b',
    r'\belectric\b',
    r'\bappliance\b',
    r'\bvacuum\b',
    r'\bblender\b', # KitchenAid mixers might get caught, but they are electric.
    r'\bmixer\b',
]

def calculate_score(item):
    """
    Calculates a 'Money Maker Score' (0-100+).
    """
    title = item['title'].lower()
    score = 0
    
    # 1. Keyword Scoring
    for pattern, points in HIGH_VALUE_PATTERNS.items():
        if re.search(pattern, title):
            score += points
            
    # 2. Negative Filtering (Strong Penalty)
    for pattern in NEGATIVE_PATTERNS:
        if re.search(pattern, title):
            score -= 100 # Kill the score immediately
            
    # 3. Price Logic
    # Vintage items are often undervalued.
    price = item['price']
    
    # Bonus for very cheap items with keywords (e.g. a $5 signed print)
    if price < 15 and score > 20:
        score += 15
    
    # Penalty for very high price items (high risk)
    if price > 300:
        score -= 10
        
    return max(0, score)

def analyze_items():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Add score column if not exists
    try:
        c.execute('ALTER TABLE items ADD COLUMN score INTEGER DEFAULT 0')
    except:
        pass
        
    c.execute("SELECT * FROM items")
    rows = c.fetchall()
    
    updates = []
    for row in rows:
        item = dict(row)
        score = calculate_score(item)
        updates.append((score, item['id']))
        
    c.executemany("UPDATE items SET score = ? WHERE id = ?", updates)
    conn.commit()
    print(f"Analyzed {len(updates)} items.")
    conn.close()

if __name__ == "__main__":
    analyze_items()
