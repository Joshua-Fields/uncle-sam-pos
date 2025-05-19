import os
import sqlite3

# Build the absolute path to the DB
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'data', 'orders.db')

# First clear and reset everything
with sqlite3.connect(DB_PATH) as conn:
    cursor = conn.cursor()

    # Clear all data
    cursor.execute("DELETE FROM orders")
    cursor.execute("DELETE FROM tickets")
    cursor.execute("DELETE FROM full_orders")

    # Reset AUTOINCREMENT counters
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='orders'")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='tickets'")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='full_orders'")

# Now VACUUM in a new connection (outside of transaction)
with sqlite3.connect(DB_PATH) as conn:
    conn.execute("VACUUM")

print("✅ Database fully reset: all data, counters, and size cleared.")
