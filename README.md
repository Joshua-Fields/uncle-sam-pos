# Uncle Sam POS

A lightweight point-of-sale (POS) system built with Flask and Supabase for persistent storage. Designed for food stands and small shops, Uncle Sam POS supports order entry, ticketing, full-order history, reporting, and an admin dashboard with robust deletion and database reset functionality.

---

## Features

* **Order Entry & Tickets**: Create orders, view live tickets, and clear individual tickets.
* **Full Orders**: Submit complete orders with combo options and lemonade upgrades.
* **Display Order Numbers**: Auto-generated `YYYYMMDD-XXX` identifiers per day.
* **Admin Dashboard**: Secure admin login (PIN-protected) for viewing, individual/multi deletion, and date-based cleanup.
* **Database Reset**: Full wipe with ID sequence restart via Supabase RPC (with fallback deletion).
* **Reporting & CSV Export**: Filtered stats by day/week, popular items, hourly breakdowns, and downloadable CSV.
* **Timezone-Aware Timestamps**: All times displayed in Europe/London locale.

---

## Tech Stack

* **Backend**: Flask (Python)
* **Database**: Supabase (PostgreSQL + PostgREST)
* **Frontend**: Vanilla JS, Chart.js for reports
* **Deployment**: Render

---

## Requirements

* Python 3.9+
* Dependencies listed in `requirements.txt`
* Supabase project with the following:

  * Tables: `orders`, `tickets`, `full_orders`
  * RPC function `truncate_all_tables()` (SECURITY DEFINER, restart identity)

---

## Installation & Setup

1. **Clone the repo**

   ```bash
   git clone https://github.com/your-username/uncle-sam-pos.git
   cd uncle-sam-pos
   ```

2. **Create a Python virtual environment**

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # on Windows: venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   Create a `.env` file in the project root:

   ```dotenv
   SUPABASE_URL=https://xyzcompany.supabase.co
   SUPABASE_KEY=<your_service_role_key>
   SECRET_KEY=<your_flask_secret>
   ```

5. **Database RPC function**
   In Supabase SQL editor, run:

   ```sql
   create or replace function truncate_all_tables()
   returns void language plpgsql security definer as $$
   begin
     truncate table public.orders,
                    public.tickets,
                    public.full_orders
       restart identity cascade;
   end;
   $$;
   alter function truncate_all_tables() owner to postgres;
   grant execute on function truncate_all_tables() to public;
   ```

---

## Running Locally

```bash
# Ensure .env is populated
python app.py        # or: gunicorn app:app --bind 0.0.0.0:5000
```

Visit [http://127.0.0.1:5000](http://127.0.0.1:5000) to access the POS. Admin panel at `/admin` (PIN: `8121` by default).

---

## Deployment to Render

1. Commit your code and push to GitHub.
2. In Render dashboard, create a new Web Service linked to your repo.
3. Set the **Start Command** to:

   ```bash
   ```

gunicorn app\:app --bind 0.0.0.0:\$PORT

```
4. Add environment variables (`SUPABASE_URL`, `SUPABASE_KEY`, `SECRET_KEY`) in Render settings.
5. Deploy — Render will install dependencies and start Gunicorn.

---

## Contributing

Pull requests are welcome! Please open issues for bugs or feature requests.

---

## License

MIT © Your Name

```
