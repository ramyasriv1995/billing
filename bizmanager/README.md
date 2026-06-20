# Smart Billing and Inventory App

A Streamlit web application for **billing**, **inventory management**, **customer management**, and **sales management**, built with Python and MongoDB.

## Features

- **Login** — Secure user authentication (default: `admin` / `admin123`)
- **Inventory** — Add, edit, delete products; adjust stock; search and filter
- **Customers** — Manage customer name, address, and GST details
- **Suppliers** — Add, update, delete and search supplier records
- **Professional Billing** — Seller and customer details, stock-aware vegetable line
  items, tax/discount totals, PDF and Excel downloads, and printer support
- **Reports** — Sales, inventory and payment reports with Excel/PDF export
- **Settings** — Company profile, invoice defaults and database backup/restore

## Requirements

- Python 3.10+
- MongoDB (local or remote)
- Streamlit
- Pillow
- pymongo
- openpyxl
- reportlab

## Installation

```bash
cd bizmanager
python3 -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
streamlit run streamlit_app.py
```

The previous launch command also remains supported:

```bash
python main.py
```

Sign in with the default credentials:

| Username | Password  |
|----------|-----------|
| admin    | admin123  |

## Database

MongoDB database `bizmanager` is created automatically on first run.

Default connection: `mongodb://localhost:27017`

Override with environment variables:

```bash
export MONGO_URI="mongodb://localhost:27017"
export MONGO_DB_NAME="bizmanager"
```

## Project Structure

```
bizmanager/
├── streamlit_app.py     # Streamlit entry point
├── export_utils.py      # PDF, Excel and backup downloads
├── database/
│   └── db.py            # MongoDB connection and queries
└── ui/                  # Legacy desktop interface (kept for reference)
```
