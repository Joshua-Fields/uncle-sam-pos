"""
app.py - Flask application using Supabase backend
Features:
  - Persistent storage via Supabase
  - Robust JSON handling for items
  - Individual and bulk deletion of orders
  - Ticket clearing
  - Full database reset (RPC + fallback)
  - Admin authentication
  - Metrics and CSV export
"""

# --- Environment Setup ---
from dotenv import load_dotenv
load_dotenv()  # load .env

from flask import (
    Flask, render_template, request, jsonify,
    Response, redirect, url_for, session, flash
)
from functools import wraps
import os
import ast
import json
from datetime import datetime, timedelta, timezone
from supabase import create_client
from dateutil import tz
from zoneinfo import ZoneInfo

# --- Supabase Client ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Flask App ---
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "fallback_key")
ADMIN_PIN = '8121'

# --- Helpers & Filters ---
@app.template_filter('datetimeformat')
def datetimeformat(value):
    try:
        # parse the stored ISO timestamp (which is in UTC)
        dt_utc = datetime.fromisoformat(value)
        # convert it to your local zone (Europe/London)
        dt_local = dt_utc.astimezone(tz.gettz('Europe/London'))
        return dt_local.strftime('%d %b %Y, %H:%M')
    except:
        return value

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

def generate_display_order_number():
    today = datetime.now(timezone.utc).date()
    try:
        res = supabase.table('full_orders').select('timestamp').execute()
        count = sum(1 for row in (res.data or [])
                    if datetime.fromisoformat(row.get('timestamp')).date() == today)
    except Exception:
        count = 0
    return f"{today.strftime('%Y%m%d')}-{count+1:03d}"

# --- Public Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/add_order', methods=['POST'])
def add_order():
    data = request.get_json() or {}
    try:
        supabase.table('orders').insert({
            'item': data.get('item'),
            'price': data.get('price', 0)
        }).execute()
    except Exception:
        pass
    return jsonify({'status': 'success'})

@app.route('/summary', methods=['GET'])
def summary():
    res = supabase.table('orders').select('item,price').execute()
    agg = {}
    for o in (res.data or []):
        name, price = o['item'], float(o['price'])
        agg.setdefault(name, {'count': 0, 'sum': 0.0})
        agg[name]['count'] += 1
        agg[name]['sum'] += price
    return jsonify([[item, v['count'], v['sum']] for item, v in agg.items()])

@app.route('/submit_order', methods=['POST'])
def submit_order():
    data = request.get_json() or {}
    payload = {
        'items': data.get('items', []),
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
    try:
        supabase.table('tickets').insert(payload).execute()
    except Exception:
        pass
    return jsonify({'status': 'submitted'})

@app.route('/get_tickets')
def get_tickets():
    t_res = supabase.table('tickets').select('*').execute()
    f_res = supabase.table('full_orders').select('timestamp,display_order_number').execute()
    lookup = {f['timestamp']: f['display_order_number'] for f in (f_res.data or [])}
    tickets = []
    for t in (t_res.data or []):
        raw = t.get('items')
        items = raw if not isinstance(raw, str) else (ast.literal_eval(raw) if raw else [])
        tickets.append({
            'id': t['id'],
            'items': items,
            'timestamp': t['timestamp'],
            'display_order_number': lookup.get(t['timestamp'])
        })
    return jsonify(tickets)

@app.route('/clear_ticket/<int:ticket_id>', methods=['DELETE'])
def clear_ticket(ticket_id):
    try:
        supabase.table('tickets').delete().filter('id','eq',str(ticket_id)).execute()
    except Exception:
        pass
    return jsonify({'status': 'cleared'})

@app.route('/tickets')
def ticket_board():
    return render_template('tickets.html')

@app.route('/save_full_order', methods=['POST'])
def save_full_order():
    data = request.get_json() or {}
    ts = datetime.now(timezone.utc).isoformat()
    disp = generate_display_order_number()
    full_payload = {
        'items': data.get('items', []),
        'total_price': data.get('total_price', 0.0),
        'timestamp': ts,
        'combo': int(data.get('combo', False)),
        'lemonade_upgrade': int(data.get('lemonade_upgrade', False)),
        'order_type': data.get('order_type', 'standard'),
        'display_order_number': disp
    }
    try: supabase.table('full_orders').insert(full_payload).execute()
    except Exception: pass
    ticket_payload = {'items': data.get('items', []), 'timestamp': ts}
    try: supabase.table('tickets').insert(ticket_payload).execute()
    except Exception: pass
    return jsonify({'status': 'saved', 'display_order_number': disp})

@app.route('/report')
def report():
    """Render report page and supply full order history for client-side display."""
    # Fetch full order history
    res = supabase.table('full_orders') \
        .select('display_order_number,timestamp,items') \
        .order('timestamp', desc=True) \
        .execute()
    history = res.data or []
    return render_template('report.html', history=history)

@app.route('/api/report_data')
def report_data():
    filter_type = request.args.get('filter', 'day')
    now = datetime.now(timezone.utc)
    # Determine filter start timestamp (UTC midnight)
    if filter_type == 'day':
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif filter_type == 'week':
        start = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    else:
        start = None

    # Query with safe filter
    if start:
        iso_start = start.strftime('%Y-%m-%dT%H:%M:%SZ')
        try:
            res = supabase.table('full_orders') \
                .select('*') \
                .filter('timestamp', 'gte', iso_start) \
                .order('timestamp', desc=False) \
                .execute()
        except Exception:
            res = supabase.table('full_orders').select('*').execute()
    else:
        res = supabase.table('full_orders').select('*') \
            .order('timestamp', desc=False).execute()

    orders = res.data or []
    # Aggregations
    total_orders = len(orders)
    total_revenue = sum(o.get('total_price', 0.0) for o in orders)
    avg_order = (total_revenue / total_orders) if total_orders else 0.0
    combo_count = sum(o.get('combo', 0) for o in orders)
    lemonade_upgrades = sum(o.get('lemonade_upgrade', 0) for o in orders)

    # Popular items
    item_counts = {}
    for o in orders:
        raw = o.get('items')
        items = raw if not isinstance(raw, str) else (ast.literal_eval(raw) if raw else [])
        for it in items:
            name = it.get('item')
            item_counts[name] = item_counts.get(name, 0) + 1
    most_popular = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    # Orders by hour
    orders_by_hour = {}
    for o in orders:
        # parse the ISO timestamp (aware UTC), then convert to London time
        dt_utc = datetime.fromisoformat(o.get('timestamp'))
        dt_local = dt_utc.astimezone(ZoneInfo('Europe/London'))
        hr = dt_local.strftime('%H:00')
        orders_by_hour[hr] = orders_by_hour.get(hr, 0) + 1

    # Detailed orders
    detailed = []
    for o in orders:
        raw = o.get('items')
        items = raw if not isinstance(raw, str) else (ast.literal_eval(raw) if raw else [])
        detailed.append({
            'display_order_number': o.get('display_order_number'),
            'total_price': o.get('total_price'),
            'items': items
        })

    return jsonify({
        'total_orders': total_orders,
        'total_revenue': round(total_revenue, 2),
        'avg_order': round(avg_order, 2),
        'combo_count': combo_count,
        'lemonade_upgrades': lemonade_upgrades,
        'most_popular': most_popular,
        'orders_by_hour': orders_by_hour,
        'orders': detailed
    })


@app.route('/export_report')
def export_report():
    filter_type = request.args.get('filter', 'day')
    now = datetime.now(timezone.utc)

    # Determine start-of-day or start-of-week
    if filter_type == 'day':
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif filter_type == 'week':
        start = (now - timedelta(days=now.weekday())) \
            .replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        start = None

    # Fetch orders with optional timestamp filter
    if start:
        iso_start = start.strftime('%Y-%m-%dT%H:%M:%SZ')
        try:
            res = supabase.table('full_orders') \
                .select('*') \
                .filter('timestamp', 'gte', iso_start) \
                .order('timestamp', desc=False) \
                .execute()
        except Exception:
            res = supabase.table('full_orders').select('*').execute()
    else:
        res = supabase.table('full_orders') \
            .select('*') \
            .order('timestamp', desc=False) \
            .execute()

    orders = res.data or []

    # Prepare CSV headers
    headers = [
        'display_order_number',
        'timestamp',
        'total_price',
        'combo',
        'lemonade_upgrade',
        'order_type',
        'items'
    ]

    def generate():
        # Yield header row
        yield ','.join(headers) + '\n'

        for o in orders:
            # Ensure items is a JSON list
            raw = o.get('items')
            items_list = (
                raw if not isinstance(raw, str)
                else (ast.literal_eval(raw) if raw else [])
            )
            items_str = json.dumps(items_list).replace(',', ';')

            row = [
                str(o.get('display_order_number', '')).replace(',', ';'),
                o.get('timestamp', '').replace(',', ';'),
                str(o.get('total_price', '')).replace(',', ';'),
                str(o.get('combo', '')).replace(',', ';'),
                str(o.get('lemonade_upgrade', '')).replace(',', ';'),
                o.get('order_type', '').replace(',', ';'),
                items_str
            ]
            yield ','.join(row) + '\n'

    return Response(
        generate(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=report_{filter_type}.csv'}
    )


# --- Admin Routes ---
@app.route('/admin', methods=['GET','POST'])
def admin_login():
    if request.method=='POST':
        if request.form.get('pin') == ADMIN_PIN:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        flash('Incorrect PIN')
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    res = supabase.table('full_orders').select('id,display_order_number,total_price,timestamp,items').order('timestamp',desc=True).execute()
    orders=[]
    for o in (res.data or []):
        raw=o.get('items')
        lst = raw if not isinstance(raw, str) else (ast.literal_eval(raw) if raw else [])
        orders.append({
            'id':o.get('id'),
            'display_number':o.get('display_order_number'),
            'total':o.get('total_price'),
            'timestamp':o.get('timestamp'),
            'timestamp_pretty':datetimeformat(o.get('timestamp')),
            'items':lst
        })
    return render_template('admin_dashboard.html', orders=orders)

@app.route('/admin/delete_order/<int:order_id>', methods=['POST'])
@admin_required
def delete_order(order_id):
    try:
        supabase.table('full_orders').delete().filter('id','eq',str(order_id)).execute()
        fr = supabase.table('full_orders').select('timestamp').execute()
        valid_ts = [f['timestamp'] for f in (fr.data or [])]
        supabase.table('tickets').delete().filter('timestamp','not.in',f"({','.join(valid_ts)})").execute()
    except Exception as e:
        flash(f'Error deleting order: {e}')
    else:
        flash(f'Order #{order_id} deleted')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_before', methods=['POST'])
@admin_required
def delete_orders_before():
    try:
        cutoff = datetime.fromisoformat(request.form.get('cutoff'))
    except:
        flash('Invalid date'); return redirect(url_for('admin_dashboard'))
    supabase.table('full_orders').delete().gt('timestamp', cutoff.isoformat()).execute()
    supabase.table('tickets').delete().gt('timestamp', cutoff.isoformat()).execute()
    flash(f'Deleted orders before {cutoff.date()}')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/reset_db', methods=['POST'])
@admin_required
def reset_database():
    # Fully wipe all tables via RPC and reset ID sequences
    if request.form.get('confirm') == 'RESET':
        try:
            # Call the truncate_all_tables RPC
            supabase.rpc('truncate_all_tables', {}).execute()
        except (json.JSONDecodeError, ValueError):
            # Supabase returns an empty body or raises ValueError on parse—ignore
            pass
        except Exception as e:
            flash(f"Error resetting database: {e}")
            return redirect(url_for('admin_dashboard'))

        flash("✅ Database fully wiped and ID sequences restarted.")
    else:
        flash("Reset aborted. Confirmation not matched.")
    return redirect(url_for('admin_dashboard'))




@app.route('/admin/delete_selected', methods=['POST'])
@admin_required
def delete_selected_orders():
    ids = request.form.getlist('delete_ids')
    if not ids:
        flash('No orders selected'); return redirect(url_for('admin_dashboard'))
    try:
        supabase.table('full_orders').delete().filter('id','in',f"({','.join(ids)})").execute()
        fr = supabase.table('full_orders').select('timestamp').execute()
        valid_ts = [f['timestamp'] for f in (fr.data or [])]
        supabase.table('tickets').delete().filter('timestamp','not.in',f"({','.join(valid_ts)})").execute()
    except Exception as e:
        flash(f'Error deleting selected: {e}')
    else:
        flash(f'Deleted {len(ids)} orders')
    return redirect(url_for('admin_dashboard'))

if __name__=='__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
