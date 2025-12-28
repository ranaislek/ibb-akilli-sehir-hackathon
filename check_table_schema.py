import psycopg2

conn = psycopg2.connect(
    host='localhost',
    port=5432,
    database='complaints_db',
    user='istanbuilders',
    password='istanbuilders123'
)

cur = conn.cursor()
cur.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'complaints'
    ORDER BY ordinal_position
""")

print("Complaints table columns:")
for row in cur.fetchall():
    print(f"  - {row[0]} ({row[1]})")

cur.close()
conn.close()
