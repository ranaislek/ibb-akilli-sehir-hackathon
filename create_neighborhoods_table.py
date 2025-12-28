import re
import psycopg2
import hashlib
from typing import Dict, List, Tuple

# Database connection
conn = psycopg2.connect(
    host='localhost',
    port=5432,
    database='complaints_db',
    user='istanbuilders',
    password='istanbuilders123'
)
cur = conn.cursor()

# Read neighborhoods.sql and extract Istanbul neighborhoods
print("Reading neighborhoods.sql...")
with open('enlem_boylam_data/neighborhoods.sql', 'r', encoding='utf-8') as f:
    content = f.read()

# Extract Istanbul neighborhoods - pattern: ('id','İstanbul','district','name','town',zipcode)
# Some entries might have NULL values, so we need flexible matching
pattern = r"\('([^']+)','İstanbul','([^']+)','([^']+)','([^']+)',(?:(\d+)|NULL)\)"
matches = re.findall(pattern, content)

print(f"Found {len(matches)} Istanbul neighborhoods")

# Get district boundaries from pk_ilce
cur.execute("""
    SELECT ilce_adi, lat, lng, northeast_lat, northeast_lng, southwest_lat, southwest_lng
    FROM pk_ilce
    WHERE il_id = 34
""")
districts = {}
for row in cur.fetchall():
    districts[row[0].upper()] = {
        'center_lat': row[1],
        'center_lng': row[2],
        'ne_lat': row[3],
        'ne_lng': row[4],
        'sw_lat': row[5],
        'sw_lng': row[6]
    }

print(f"Loaded {len(districts)} districts with boundaries")

# District name mappings for variations in data
district_mapping = {
    'EYÜPSULTAN': 'EYÜP',
    'BEYLİKDÜZÜ': 'BEYLİKDÜZÜ',
    'BEŞIKTAŞ': 'BEŞİKTAŞ',
    'BEYLIKDÜZÜ': 'BEYLİKDÜZÜ',
    'SULTANBEYLI': 'SULTANBEYLİ',
    'BAŞAKŞEHIR': 'BAŞAKŞEHİR',
    'ŞIŞLI': 'ŞİŞLİ',
    'BAHÇELIEVLER': 'BAHÇELİEVLER',
    'ÜMRANIYE': 'ÜMRANİYE',
    'ATAŞEHIR': 'ATAŞEHİR',
    'SILIVRI': 'SİLİVRİ',
    'EYÜPSULTAN': 'EYÜP',
    'GAZIOSMANPAŞA': 'GAZİOSMANPAŞA',
    'FATIH': 'FATİH',
    'ZEYTINBURNU': 'ZEYTİNBURNU',
    'PENDIK': 'PENDİK',
    'SULTANGAZI': 'SULTANGAZİ',
    'ŞILE': 'ŞİLE',
}

# Create pk_mahalle table
print("Creating pk_mahalle table...")
cur.execute("DROP TABLE IF EXISTS pk_mahalle CASCADE")
cur.execute("""
    CREATE TABLE pk_mahalle (
        mahalle_id SERIAL PRIMARY KEY,
        ilce_adi VARCHAR(255) NOT NULL,
        mahalle_adi VARCHAR(255) NOT NULL,
        posta_kodu INTEGER,
        lat DOUBLE PRECISION NOT NULL,
        lng DOUBLE PRECISION NOT NULL,
        UNIQUE(ilce_adi, mahalle_adi)
    )
""")

def calculate_distributed_coordinates(district_name: str, neighborhood_name: str, 
                                     district_info: Dict, index: int, total: int) -> Tuple[float, float]:
    """
    Distribute neighborhoods within district boundaries using a quasi-random pattern.
    Uses neighborhood name hash for consistency + index for better distribution.
    """
    if not district_info['ne_lat'] or not district_info['sw_lat']:
        # Fallback to center if no boundaries
        return district_info['center_lat'], district_info['center_lng']
    
    # Calculate district dimensions
    lat_range = district_info['ne_lat'] - district_info['sw_lat']
    lng_range = district_info['ne_lng'] - district_info['sw_lng']
    
    # Use hash for consistent positioning per neighborhood
    hash_value = int(hashlib.md5(neighborhood_name.encode()).hexdigest(), 16)
    
    # Create a grid-like distribution with some randomness
    # Divide district into a grid and place neighborhoods in different cells
    grid_size = max(3, int((total ** 0.5) + 1))  # At least 3x3 grid
    
    # Grid position based on index
    grid_x = (index % grid_size) / grid_size
    grid_y = (index // grid_size % grid_size) / grid_size
    
    # Add hash-based offset within the grid cell (±0.3 of cell size)
    cell_offset_x = ((hash_value % 1000) / 1000 - 0.5) * 0.6 / grid_size
    cell_offset_y = (((hash_value // 1000) % 1000) / 1000 - 0.5) * 0.6 / grid_size
    
    # Calculate final position with 10% margin from boundaries
    margin = 0.1
    lat = district_info['sw_lat'] + (margin + (1 - 2*margin) * (grid_y + cell_offset_y)) * lat_range
    lng = district_info['sw_lng'] + (margin + (1 - 2*margin) * (grid_x + cell_offset_x)) * lng_range
    
    return round(lat, 7), round(lng, 7)

# Group neighborhoods by district (town field contains the actual district name)
neighborhoods_by_district = {}
for _id, district_area, neighborhood_name, actual_district, zipcode in matches:
    district_upper = actual_district.upper()
    # Apply district name mapping if needed
    district_upper = district_mapping.get(district_upper, district_upper)
    
    if district_upper not in neighborhoods_by_district:
        neighborhoods_by_district[district_upper] = []
    neighborhoods_by_district[district_upper].append({
        'name': neighborhood_name,
        'zipcode': int(zipcode) if zipcode and zipcode.isdigit() else None
    })

print(f"\nProcessing {len(neighborhoods_by_district)} districts...")

# Insert neighborhoods with distributed coordinates
inserted = 0
skipped = 0

for district_name, neighborhoods in neighborhoods_by_district.items():
    if district_name not in districts:
        print(f"  Warning: District '{district_name}' not found in pk_ilce table, skipping {len(neighborhoods)} neighborhoods")
        skipped += len(neighborhoods)
        continue
    
    district_info = districts[district_name]
    total_in_district = len(neighborhoods)
    
    for idx, neighborhood in enumerate(neighborhoods):
        lat, lng = calculate_distributed_coordinates(
            district_name, 
            neighborhood['name'], 
            district_info, 
            idx, 
            total_in_district
        )
        
        try:
            cur.execute("""
                INSERT INTO pk_mahalle (ilce_adi, mahalle_adi, posta_kodu, lat, lng)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (ilce_adi, mahalle_adi) DO NOTHING
            """, (district_name, neighborhood['name'], neighborhood['zipcode'], lat, lng))
            inserted += 1
        except Exception as e:
            print(f"  Error inserting {district_name}/{neighborhood['name']}: {e}")
            skipped += 1
    
    print(f"  {district_name}: {total_in_district} neighborhoods distributed within boundaries")

conn.commit()

# Verify results
cur.execute("SELECT COUNT(*) FROM pk_mahalle")
total = cur.fetchone()[0]

cur.execute("SELECT ilce_adi, COUNT(*) FROM pk_mahalle GROUP BY ilce_adi ORDER BY COUNT(*) DESC LIMIT 10")
top_districts = cur.fetchall()

print(f"\n✅ Success!")
print(f"   Total neighborhoods inserted: {total}")
print(f"   Skipped: {skipped}")
print(f"\nTop 10 districts by neighborhood count:")
for district, count in top_districts:
    print(f"   {district}: {count} neighborhoods")

# Create index for faster queries
cur.execute("CREATE INDEX idx_mahalle_ilce ON pk_mahalle(ilce_adi)")
conn.commit()

cur.close()
conn.close()

print("\n✨ pk_mahalle table created successfully!")
print("   Neighborhoods are distributed within their district boundaries")
print("   Ready to update demo_app.py to use the new table")
