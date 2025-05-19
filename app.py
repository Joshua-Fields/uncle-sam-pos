from flask import Flask, render_template, request, jsonify, Response, redirect, url_for, session, flash
from functools import wraps
import sqlite3
import os
import csv
import ast
from datetime import datetime, timedelta
from functools import wraps
import sqlite3
from datetime import datetime

app = Flask(__name__)

DB_PATH = 'data/orders.db'

# app.secret_key = 'very_secret_key_for_session'  # Needed for session management
app.secret_key = os.getenv('SECRET_KEY', 'fallback_key')
ADMIN_PIN = '8121'


from datetime import datetime

@app.template_filter('datetimeformat')
def datetimeformat(value):
    try:
        dt = datetime.fromisoformat(value)
        return dt.strftime('%d %b %Y, %H:%M')  # e.g., 19 May 2025, 15:22
    except:
        return value  # fallback if parsing fails



# --- Auth Decorator ---
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated


app.secret_key = 'very_secret_key_for_session'

ADMIN_PIN = '8121'
DB_PATH = 'data/orders.db'

# --- Auth Decorator ---
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        pin = request.form.get('pin')
        if pin == ADMIN_PIN:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('admin_login.html', error="Incorrect PIN")
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            'SELECT id, display_order_number, total_price, timestamp, items FROM full_orders ORDER BY timestamp DESC')
        rows = cursor.fetchall()

        orders = []
        for row in rows:
            try:
                items = ast.literal_eval(row[4])
            except Exception:
                items = []
            try:
                timestamp_pretty = datetime.fromisoformat(row[3]).strftime('%d %b %Y, %H:%M')
            except Exception:
                timestamp_pretty = row[3]  # fallback

            orders.append({
                'id': row[0],
                'display_number': row[1],
                'total': row[2],
                'timestamp': row[3],  # Raw ISO string for logic or JS
                'timestamp_pretty': datetimeformat(row[3]),  # Pretty string for display

                'items': items
            })
    return render_template('admin_dashboard.html', orders=orders)

@app.route('/admin/delete_order/<int:order_id>', methods=['POST'])
@admin_required
def delete_order(order_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('DELETE FROM full_orders WHERE id = ?', (order_id,))
        conn.execute('DELETE FROM tickets WHERE timestamp NOT IN (SELECT timestamp FROM full_orders)')
    flash(f"Order #{order_id} deleted successfully.")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_before', methods=['POST'])
@admin_required
def delete_orders_before():
    cutoff = request.form.get('cutoff')
    try:
        cutoff_dt = datetime.strptime(cutoff, '%Y-%m-%d')
    except ValueError:
        flash("Invalid date format.")
        return redirect(url_for('admin_dashboard'))

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM full_orders WHERE DATE(timestamp) < ?", (cutoff_dt.date().isoformat(),))
        conn.execute("DELETE FROM tickets WHERE DATE(timestamp) < ?", (cutoff_dt.date().isoformat(),))
    flash(f"All orders before {cutoff_dt.date()} deleted.")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/reset_db', methods=['POST'])
@admin_required
def reset_database():
    confirm = request.form.get('confirm')
    if confirm == 'RESET':
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("DELETE FROM orders")
            c.execute("DELETE FROM tickets")
            c.execute("DELETE FROM full_orders")
            c.execute("DELETE FROM sqlite_sequence WHERE name='orders'")
            c.execute("DELETE FROM sqlite_sequence WHERE name='tickets'")
            c.execute("DELETE FROM sqlite_sequence WHERE name='full_orders'")
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("VACUUM")
        flash("✅ Database fully reset.")
    else:
        flash("Reset aborted. Confirmation not matched.")
    return redirect(url_for('admin_dashboard'))





def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item TEXT NOT NULL,
                price REAL NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                items TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS full_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                items TEXT NOT NULL,
                total_price REAL NOT NULL,
                timestamp TEXT NOT NULL,
                combo INTEGER DEFAULT 0,
                lemonade_upgrade INTEGER DEFAULT 0,
                order_type TEXT
            )
        ''')

def generate_display_order_number():
    today = datetime.now().strftime('%Y%m%d')
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            "SELECT COUNT(*) FROM full_orders WHERE DATE(timestamp) = DATE('now')"
        )
        daily_count = cursor.fetchone()[0] + 1
    return f"{today}-{daily_count:03d}"


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/add_order', methods=['POST'])
def add_order():
    data = request.get_json()
    item = data['item']
    price = data['price']
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('INSERT INTO orders (item, price) VALUES (?, ?)', (item, price))
    return jsonify({"status": "success"})

@app.route('/summary', methods=['GET'])
def summary():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute('SELECT item, COUNT(*), SUM(price) FROM orders GROUP BY item')
        results = cursor.fetchall()
    return jsonify(results)

@app.route('/submit_order', methods=['POST'])
def submit_order():
    data = request.get_json()
    items = data['items']
    timestamp = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            INSERT INTO tickets (items, timestamp)
            VALUES (?, ?)
        ''', (str(items), timestamp))

    return jsonify({"status": "submitted"})

@app.route('/get_tickets')
def get_tickets():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute('''
            SELECT t.id, t.items, t.timestamp, f.display_order_number
            FROM tickets t
            LEFT JOIN full_orders f ON t.timestamp = f.timestamp
        ''')
        tickets = [
            {
                "id": row[0],
                "items": ast.literal_eval(row[1]),  # ✅ this is the 'items' column
                "timestamp": row[2],
                "display_order_number": row[3]
            }
            for row in cursor.fetchall()
        ]

    return jsonify(tickets)




@app.route('/clear_ticket/<int:ticket_id>', methods=['DELETE'])
def clear_ticket(ticket_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('DELETE FROM tickets WHERE id = ?', (ticket_id,))
    return jsonify({"status": "cleared"})

@app.route('/tickets')
def ticket_board():
    return render_template('tickets.html')

@app.route('/save_full_order', methods=['POST'])
def save_full_order():
    data = request.get_json()

    items = data.get('items', [])
    total_price = data.get('total_price', 0.0)
    combo = int(data.get('combo', False))
    lemonade_upgrade = int(data.get('lemonade_upgrade', False))
    order_type = data.get('order_type', 'standard')
    timestamp = datetime.now().isoformat()
    display_number = generate_display_order_number()

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            INSERT INTO full_orders (items, total_price, timestamp, combo, lemonade_upgrade, order_type, display_order_number)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (str(items), total_price, timestamp, combo, lemonade_upgrade, order_type, display_number))

        conn.execute('''
            INSERT INTO tickets (items, timestamp)
            VALUES (?, ?)
        ''', (str(items), timestamp))

    return jsonify({'status': 'saved', 'display_order_number': display_number})


@app.route('/report')
def report():
    return render_template('report.html')

@app.route('/api/report_data')
def report_data():
    filter_type = request.args.get('filter', 'day')

    now = datetime.now()
    if filter_type == 'day':
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif filter_type == 'week':
        start = now - timedelta(days=now.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        start = datetime.min

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()

        c.execute('''
            SELECT COUNT(*), SUM(total_price), AVG(total_price)
            FROM full_orders
            WHERE timestamp >= ?
        ''', (start.isoformat(),))
        total_orders, total_revenue, avg_order = c.fetchone()

        c.execute('''
            SELECT COUNT(*) FROM full_orders
            WHERE combo = 1 AND timestamp >= ?
        ''', (start.isoformat(),))
        combo_count = c.fetchone()[0]

        c.execute('''
            SELECT COUNT(*) FROM full_orders
            WHERE lemonade_upgrade = 1 AND timestamp >= ?
        ''', (start.isoformat(),))
        lemonade_upgrades = c.fetchone()[0]

        # All orders with display numbers + items
        c.execute('''
            SELECT display_order_number, total_price, items
            FROM full_orders
            WHERE timestamp >= ?
        ''', (start.isoformat(),))
        orders = [
            {
                "display_order_number": row[0],
                "total_price": row[1],
                "items": eval(row[2])  # Parse item list from string
            }
            for row in c.fetchall()
        ]

        c.execute('SELECT items, timestamp FROM full_orders WHERE timestamp >= ?', (start.isoformat(),))
        item_counts = {}
        for row in c.fetchall():
            order_items = ast.literal_eval(row[0])
            for item in order_items:
                name = item['item']
                item_counts[name] = item_counts.get(name, 0) + 1

        most_popular = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)

        c.execute('SELECT timestamp FROM full_orders WHERE timestamp >= ?', (start.isoformat(),))
        hour_counts = {}
        for row in c.fetchall():
            dt = datetime.fromisoformat(row[0])
            hour = dt.strftime('%H:00')
            hour_counts[hour] = hour_counts.get(hour, 0) + 1

        return jsonify({
            'total_orders': total_orders or 0,
            'total_revenue': round(total_revenue or 0, 2),
            'avg_order': round(avg_order or 0, 2),
            'combo_count': combo_count,
            'lemonade_upgrades': lemonade_upgrades,
            'most_popular': most_popular[:5],
            'orders_by_hour': hour_counts,
            'orders': orders  # 👈 added here
        })


@app.route('/export_report')
def export_report():
    filter_type = request.args.get('filter', 'day')

    now = datetime.now()
    if filter_type == 'day':
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif filter_type == 'week':
        start = now - timedelta(days=now.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        start = datetime.min

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM full_orders WHERE timestamp >= ?', (start.isoformat(),))
        orders = c.fetchall()
        headers = [description[0] for description in c.description]

    def generate():
        yield ','.join(headers) + '\n'
        for row in orders:
            formatted = [str(cell).replace('\n', ' ').replace(',', ';') for cell in row]
            yield ','.join(formatted) + '\n'

    return Response(
        generate(),
        mimetype='text/csv',
        headers={"Content-Disposition": f"attachment;filename=uncle_sams_report_{filter_type}.csv"}
    )

@app.route('/admin/delete_selected', methods=['POST'])
@admin_required
def delete_selected_orders():
    ids = request.form.getlist('delete_ids')
    if ids:
        with sqlite3.connect(DB_PATH) as conn:
            for order_id in ids:
                conn.execute('DELETE FROM full_orders WHERE id = ?', (order_id,))
            conn.execute('DELETE FROM tickets WHERE timestamp NOT IN (SELECT timestamp FROM full_orders)')
        flash(f"🗑 Deleted {len(ids)} selected order(s).")
    else:
        flash("⚠️ No orders selected.")
    return redirect(url_for('admin_dashboard'))



if __name__ == '__main__':
    init_db()
    # app.run(debug=True)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
