import hashlib
import json
import os
import re
import secrets
from datetime import datetime

from bson import ObjectId, json_util
from pymongo import ASCENDING, MongoClient, ReturnDocument

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.environ.get("MONGO_DB_NAME", "bizmanager")

_client: MongoClient | None = None
_db = None


def get_db():
    global _client, _db
    if _db is None:
        _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        _db = _client[DB_NAME]
    return _db


def _serialize_doc(doc):
    if not doc:
        return None
    result = {k: v for k, v in doc.items() if k != "_id"}
    result["id"] = str(doc["_id"])
    return result


def _oid(id_value):
    if isinstance(id_value, ObjectId):
        return id_value
    return ObjectId(str(id_value))


def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()


def _create_password_record(password: str) -> tuple[str, str]:
    salt = secrets.token_hex(16)
    return _hash_password(password, salt), salt


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today_date() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _ensure_indexes(db):
    db.categories.create_index([("name", ASCENDING)], unique=True)
    db.products.create_index([("name", ASCENDING)])
    db.customers.create_index([("name", ASCENDING)])
    db.customers.create_index([("gst", ASCENDING)])
    db.suppliers.create_index([("name", ASCENDING)])
    db.sales.create_index([("invoice_number", ASCENDING)], unique=True)
    db.sales.create_index([("created_at", ASCENDING)])
    db.users.create_index([("username", ASCENDING)], unique=True)


def init_db():
    db = get_db()
    _ensure_indexes(db)
    # Remove the retired SKU field and its legacy index from existing databases.
    if "sku_1" in db.products.index_information():
        db.products.drop_index("sku_1")
    db.products.update_many({"sku": {"$exists": True}}, {"$unset": {"sku": ""}})

    if db.categories.count_documents({}) == 0:
        defaults = ["Vegetables", "Leafy Greens", "Fruits", "Herbs", "Other"]
        db.categories.insert_many([{"name": name} for name in defaults])

    if db.users.count_documents({}) == 0:
        password_hash, salt = _create_password_record("admin123")
        db.users.insert_one({
            "username": "admin",
            "password_hash": password_hash,
            "salt": salt,
            "full_name": "Administrator",
            "created_at": now_iso(),
        })


# --- Users ---

def authenticate_user(username: str, password: str):
    db = get_db()
    user = db.users.find_one({"username": username.strip()})
    if not user:
        return None
    if _hash_password(password, user["salt"]) != user["password_hash"]:
        return None
    return {
        "id": str(user["_id"]),
        "username": user["username"],
        "full_name": user.get("full_name"),
    }


def add_user(username: str, password: str, full_name: str = "") -> str:
    password_hash, salt = _create_password_record(password)
    db = get_db()
    result = db.users.insert_one({
        "username": username.strip(),
        "password_hash": password_hash,
        "salt": salt,
        "full_name": full_name.strip(),
        "created_at": now_iso(),
    })
    return str(result.inserted_id)


# --- Categories ---

def get_categories():
    db = get_db()
    return [_serialize_doc(c) for c in db.categories.find().sort("name", ASCENDING)]


def add_category(name: str) -> str:
    db = get_db()
    result = db.categories.insert_one({"name": name.strip()})
    return str(result.inserted_id)


# --- Products ---

def _category_map(db):
    return {str(c["_id"]): c["name"] for c in db.categories.find()}


def get_products(search: str = ""):
    db = get_db()
    categories = _category_map(db)
    products = []
    for doc in db.products.find().sort("name", ASCENDING):
        product = _serialize_doc(doc)
        cat_id = product.get("category_id")
        product["category_name"] = categories.get(str(cat_id)) if cat_id else None
        products.append(product)

    if not search:
        return products

    term = search.strip().lower()
    return [
        p for p in products
        if term in (p.get("name") or "").lower()
        or term in (p.get("category_name") or "").lower()
    ]


def get_product(product_id):
    db = get_db()
    doc = db.products.find_one({"_id": _oid(product_id)})
    if not doc:
        return None
    product = _serialize_doc(doc)
    if product.get("category_id"):
        cat = db.categories.find_one({"_id": _oid(product["category_id"])})
        product["category_name"] = cat["name"] if cat else None
    return product


def add_product(data: dict) -> str:
    ts = now_iso()
    db = get_db()
    doc = {
        "name": data["name"],
        "category_id": str(data["category_id"]) if data.get("category_id") else None,
        "cost_price": float(data.get("cost_price", 0)),
        "selling_price": float(data.get("selling_price", 0)),
        "stock_quantity": float(data.get("stock_quantity", 0)),
        "min_stock_level": float(data.get("min_stock_level", 5)),
        "unit": data.get("unit", "kg") or "kg",
        "description": data.get("description", ""),
        "created_at": ts,
        "updated_at": ts,
    }
    result = db.products.insert_one(doc)
    return str(result.inserted_id)


def update_product(product_id, data: dict):
    db = get_db()
    db.products.update_one(
        {"_id": _oid(product_id)},
        {"$set": {
            "name": data["name"],
            "category_id": str(data["category_id"]) if data.get("category_id") else None,
            "cost_price": float(data.get("cost_price", 0)),
            "selling_price": float(data.get("selling_price", 0)),
            "stock_quantity": float(data.get("stock_quantity", 0)),
            "min_stock_level": float(data.get("min_stock_level", 5)),
            "unit": data.get("unit", "kg") or "kg",
            "description": data.get("description", ""),
            "updated_at": now_iso(),
        }},
    )


def delete_product(product_id):
    db = get_db()
    db.products.delete_one({"_id": _oid(product_id)})


def adjust_stock(product_id, quantity_change: float):
    db = get_db()
    db.products.update_one(
        {"_id": _oid(product_id)},
        {
            "$inc": {"stock_quantity": quantity_change},
            "$set": {"updated_at": now_iso()},
        },
    )


def get_low_stock_products():
    db = get_db()
    pipeline = [
        {"$match": {"$expr": {"$lte": ["$stock_quantity", "$min_stock_level"]}}},
        {"$sort": {"stock_quantity": ASCENDING}},
    ]
    return [_serialize_doc(doc) for doc in db.products.aggregate(pipeline)]


# --- Customers ---

def get_customers(search: str = ""):
    db = get_db()
    query = {}
    if search:
        term = re.escape(search.strip())
        query = {
            "$or": [
                {"name": {"$regex": term, "$options": "i"}},
                {"address": {"$regex": term, "$options": "i"}},
                {"gst": {"$regex": term, "$options": "i"}},
                {"phone": {"$regex": term, "$options": "i"}},
                {"email": {"$regex": term, "$options": "i"}},
            ]
        }
    return [_serialize_doc(c) for c in db.customers.find(query).sort("name", ASCENDING)]


def get_customer(customer_id):
    db = get_db()
    doc = db.customers.find_one({"_id": _oid(customer_id)})
    return _serialize_doc(doc)


def add_customer(data: dict) -> str:
    db = get_db()
    result = db.customers.insert_one({
        "name": data["name"],
        "address": data.get("address", ""),
        "gst": data.get("gst", ""),
        "phone": data.get("phone", ""),
        "email": data.get("email", ""),
        "created_at": now_iso(),
    })
    return str(result.inserted_id)


def update_customer(customer_id, data: dict):
    db = get_db()
    db.customers.update_one(
        {"_id": _oid(customer_id)},
        {"$set": {
            "name": data["name"],
            "address": data.get("address", ""),
            "gst": data.get("gst", ""),
            "phone": data.get("phone", ""),
            "email": data.get("email", ""),
        }},
    )


def delete_customer(customer_id):
    db = get_db()
    db.customers.delete_one({"_id": _oid(customer_id)})


# --- Sales ---

def generate_invoice_number() -> str:
    prefix = datetime.now().strftime("%Y%m%d")
    db = get_db()
    settings = get_settings()
    invoice_prefix = settings.get("invoice_prefix", "INV") or "INV"
    pattern = f"^{re.escape(invoice_prefix)}-{prefix}-"
    count = db.sales.count_documents({"invoice_number": {"$regex": pattern}})
    return f"{invoice_prefix}-{prefix}-{count + 1:04d}"


def create_sale(sale_data: dict, items: list) -> str:
    db = get_db()
    reserved_items = []
    normalized_items = []
    for item in items:
        quantity = float(item["quantity"])
        if quantity <= 0:
            raise ValueError(f"Quantity for {item['product_name']} must be greater than zero.")
        product_id = item.get("product_id")
        if product_id:
            updated = db.products.find_one_and_update(
                {
                    "_id": _oid(product_id),
                    "stock_quantity": {"$gte": quantity},
                },
                {
                    "$inc": {"stock_quantity": -quantity},
                    "$set": {"updated_at": now_iso()},
                },
                return_document=ReturnDocument.AFTER,
            )
            if not updated:
                for reserved_id, reserved_quantity in reserved_items:
                    adjust_stock(reserved_id, reserved_quantity)
                product = get_product(product_id)
                available = product.get("stock_quantity", 0) if product else 0
                raise ValueError(
                    f"Insufficient stock for {item['product_name']}. "
                    f"Only {available:g} available."
                )
            reserved_items.append((product_id, quantity))
        normalized_items.append({
            "product_id": str(product_id) if product_id else None,
            "product_name": item["product_name"],
            "quantity": quantity,
            "unit": item.get("unit", "pcs"),
            "unit_price": float(item["unit_price"]),
            "subtotal": float(item.get("subtotal", quantity * float(item["unit_price"]))),
            "tax_rate": float(item.get("tax_rate", 0)),
            "tax_amount": float(item.get("tax_amount", 0)),
            "discount_rate": float(item.get("discount_rate", 0)),
            "discount_amount": float(item.get("discount_amount", 0)),
            "amount": float(item.get("amount", item.get("subtotal", 0))),
            "cost_price": float(updated.get("cost_price", 0)) if product_id else 0,
        })

    sale_doc = {
        "invoice_number": sale_data["invoice_number"],
        "customer_id": str(sale_data["customer_id"]) if sale_data.get("customer_id") else None,
        "subtotal": sale_data["subtotal"],
        "tax_rate": sale_data.get("tax_rate", 0),
        "tax_amount": sale_data["tax_amount"],
        "discount": sale_data.get("discount", 0),
        "total": sale_data["total"],
        "payment_method": sale_data.get("payment_method", "Cash"),
        "cash_received": sale_data.get("cash_received", 0),
        "balance_return": sale_data.get("balance_return", 0),
        "status": sale_data.get("status", "Completed"),
        "notes": sale_data.get("notes", ""),
        "customer_name": sale_data.get("customer_name", ""),
        "customer_phone": sale_data.get("customer_phone", ""),
        "customer_email": sale_data.get("customer_email", ""),
        "customer_address": sale_data.get("customer_address", ""),
        "customer_gst": sale_data.get("customer_gst", ""),
        "company_name": sale_data.get("company_name", ""),
        "company_phone": sale_data.get("company_phone", ""),
        "company_email": sale_data.get("company_email", ""),
        "company_address": sale_data.get("company_address", ""),
        "company_gst": sale_data.get("company_gst", ""),
        "created_at": now_iso(),
        "items": normalized_items,
    }
    try:
        result = db.sales.insert_one(sale_doc)
    except Exception:
        for reserved_id, reserved_quantity in reserved_items:
            adjust_stock(reserved_id, reserved_quantity)
        raise
    return str(result.inserted_id)


def _customer_name_map(db, customer_ids):
    ids = [_oid(cid) for cid in customer_ids if cid]
    if not ids:
        return {}
    return {
        str(c["_id"]): c["name"]
        for c in db.customers.find({"_id": {"$in": ids}})
    }


def get_sales(search: str = "", date_filter: str = ""):
    db = get_db()
    query = {}
    if date_filter:
        query["created_at"] = {"$regex": f"^{re.escape(date_filter)}"}

    sales = list(db.sales.find(query).sort("created_at", -1))
    customer_ids = [s.get("customer_id") for s in sales if s.get("customer_id")]
    names = _customer_name_map(db, customer_ids)

    results = []
    for doc in sales:
        sale = _serialize_doc(doc)
        sale["customer_name"] = sale.get("customer_name") or names.get(sale.get("customer_id"))
        if search:
            term = search.strip().lower()
            invoice = (sale.get("invoice_number") or "").lower()
            customer = (sale.get("customer_name") or "").lower()
            if term not in invoice and term not in customer:
                continue
        results.append(sale)
    return results


def get_sale(sale_id):
    db = get_db()
    doc = db.sales.find_one({"_id": _oid(sale_id)})
    if not doc:
        return None

    sale = _serialize_doc(doc)
    customer_id = sale.get("customer_id")
    if customer_id:
        customer = db.customers.find_one({"_id": _oid(customer_id)})
        if customer:
            sale["customer_name"] = sale.get("customer_name") or customer.get("name")
            sale["customer_phone"] = sale.get("customer_phone") or customer.get("phone")
            sale["customer_email"] = sale.get("customer_email") or customer.get("email")
            sale["customer_address"] = sale.get("customer_address") or customer.get("address")
            sale["customer_gst"] = sale.get("customer_gst") or customer.get("gst")

    sale["items"] = sale.pop("items", [])
    for i, item in enumerate(sale["items"]):
        item["id"] = str(i + 1)
    return sale


# --- Reports ---

def _month_names():
    return [
        "", "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ]


def _summarize_sales(sales):
    return {
        "sales_count": len(sales),
        "subtotal": sum(s.get("subtotal", 0) for s in sales),
        "tax_amount": sum(s.get("tax_amount", 0) for s in sales),
        "discount": sum(s.get("discount", 0) for s in sales),
        "total_revenue": sum(s.get("total", 0) for s in sales),
    }


def _payment_breakdown(sales):
    breakdown = {}
    for sale in sales:
        method = sale.get("payment_method", "Cash")
        if method not in breakdown:
            breakdown[method] = {"payment_method": method, "count": 0, "total": 0}
        breakdown[method]["count"] += 1
        breakdown[method]["total"] += sale.get("total", 0)
    return sorted(breakdown.values(), key=lambda x: x["total"], reverse=True)


def _top_products(sales, limit=10):
    product_stats = {}
    for sale in sales:
        for item in sale.get("items", []):
            name = item["product_name"]
            if name not in product_stats:
                product_stats[name] = {"product_name": name, "units_sold": 0, "revenue": 0}
            product_stats[name]["units_sold"] += item["quantity"]
            product_stats[name]["revenue"] += item["subtotal"]
    return sorted(product_stats.values(), key=lambda x: x["revenue"], reverse=True)[:limit]


def get_monthly_report(year: int, month: int) -> dict:
    db = get_db()
    prefix = f"{year:04d}-{month:02d}"
    sales = list(db.sales.find({"created_at": {"$regex": f"^{prefix}"}}))
    summary = _summarize_sales(sales)

    daily = {}
    for sale in sales:
        day = sale["created_at"][:10]
        if day not in daily:
            daily[day] = {"day": day, "sales_count": 0, "total": 0}
        daily[day]["sales_count"] += 1
        daily[day]["total"] += sale.get("total", 0)

    month_names = _month_names()
    return {
        "period_type": "month",
        "period_label": f"{month_names[month]} {year}",
        "year": year,
        "month": month,
        **summary,
        "payment_breakdown": _payment_breakdown(sales),
        "top_products": _top_products(sales),
        "daily_sales": sorted(daily.values(), key=lambda x: x["day"]),
    }


def get_yearly_report(year: int) -> dict:
    db = get_db()
    prefix = f"{year:04d}"
    sales = list(db.sales.find({"created_at": {"$regex": f"^{prefix}"}}))
    summary = _summarize_sales(sales)

    monthly = {}
    month_names = _month_names()
    for sale in sales:
        month_num = sale["created_at"][5:7]
        if month_num not in monthly:
            monthly[month_num] = {
                "month_num": month_num,
                "month_name": month_names[int(month_num)],
                "sales_count": 0,
                "total": 0,
            }
        monthly[month_num]["sales_count"] += 1
        monthly[month_num]["total"] += sale.get("total", 0)

    return {
        "period_type": "year",
        "period_label": str(year),
        "year": year,
        **summary,
        "monthly_breakdown": sorted(monthly.values(), key=lambda x: x["month_num"]),
        "payment_breakdown": _payment_breakdown(sales),
        "top_products": _top_products(sales),
    }


def _sales_between(start_date: str, end_date: str):
    query = {"created_at": {"$gte": f"{start_date} 00:00:00", "$lte": f"{end_date} 23:59:59"}}
    return list(get_db().sales.find(query).sort("created_at", ASCENDING))


def get_sales_report(start_date: str, end_date: str) -> dict:
    sales = _sales_between(start_date, end_date)
    products = {p["id"]: p for p in get_products()}
    product_rows = {}
    profit = 0.0
    for sale in sales:
        for item in sale.get("items", []):
            name = item.get("product_name", "Unknown")
            quantity = float(item.get("quantity", 0))
            revenue = float(item.get("amount", item.get("subtotal", 0)))
            cost_price = item.get("cost_price")
            if cost_price is None:
                product = products.get(str(item.get("product_id")))
                cost_price = product.get("cost_price", 0) if product else 0
            item_profit = revenue - (quantity * float(cost_price or 0))
            profit += item_profit
            row = product_rows.setdefault(name, {
                "product_name": name, "quantity": 0.0, "revenue": 0.0, "profit": 0.0,
            })
            row["quantity"] += quantity
            row["revenue"] += revenue
            row["profit"] += item_profit
    return {
        "report_type": "Sales Report",
        "period_label": f"{start_date} to {end_date}",
        "start_date": start_date,
        "end_date": end_date,
        "sales_count": len(sales),
        "revenue": sum(float(s.get("total", 0)) for s in sales),
        "profit": profit,
        "tax_collected": sum(float(s.get("tax_amount", 0)) for s in sales),
        "product_sales": sorted(product_rows.values(), key=lambda row: row["revenue"], reverse=True),
    }


def get_inventory_report() -> dict:
    products = get_products()
    low_stock = [p for p in products if p["stock_quantity"] <= p["min_stock_level"]]
    out_of_stock = [p for p in products if p["stock_quantity"] <= 0]
    return {
        "report_type": "Inventory Report",
        "period_label": datetime.now().strftime("%Y-%m-%d"),
        "current_stock": products,
        "low_stock": low_stock,
        "out_of_stock": out_of_stock,
        "inventory_value": sum(
            float(p.get("stock_quantity", 0)) * float(p.get("cost_price", 0))
            for p in products
        ),
        "total_units": sum(float(p.get("stock_quantity", 0)) for p in products),
    }


def get_payment_report(start_date: str, end_date: str, opening_balance=0, expenses=0) -> dict:
    sales = _sales_between(start_date, end_date)
    collections = {"Cash": 0.0, "UPI": 0.0, "Card": 0.0, "Bank Transfer": 0.0}
    for sale in sales:
        method = sale.get("payment_method", "Cash")
        collections[method] = collections.get(method, 0) + float(sale.get("total", 0))
    sales_collection = sum(collections.values())
    return {
        "report_type": "Payment Report",
        "period_label": f"{start_date} to {end_date}",
        "collections": collections,
        "opening_balance": float(opening_balance or 0),
        "sales_collection": sales_collection,
        "expenses": float(expenses or 0),
        "closing_balance": float(opening_balance or 0) + sales_collection - float(expenses or 0),
    }


# --- Suppliers ---

def get_suppliers(search: str = ""):
    query = {}
    if search:
        term = re.escape(search.strip())
        query = {"$or": [
            {"name": {"$regex": term, "$options": "i"}},
            {"phone": {"$regex": term, "$options": "i"}},
            {"email": {"$regex": term, "$options": "i"}},
            {"gst": {"$regex": term, "$options": "i"}},
        ]}
    return [_serialize_doc(doc) for doc in get_db().suppliers.find(query).sort("name", ASCENDING)]


def get_supplier(supplier_id):
    return _serialize_doc(get_db().suppliers.find_one({"_id": _oid(supplier_id)}))


def add_supplier(data: dict) -> str:
    doc = {
        "name": data["name"].strip(),
        "phone": data.get("phone", "").strip(),
        "email": data.get("email", "").strip(),
        "address": data.get("address", "").strip(),
        "gst": data.get("gst", "").strip(),
        "created_at": now_iso(),
    }
    return str(get_db().suppliers.insert_one(doc).inserted_id)


def update_supplier(supplier_id, data: dict):
    get_db().suppliers.update_one({"_id": _oid(supplier_id)}, {"$set": {
        "name": data["name"].strip(),
        "phone": data.get("phone", "").strip(),
        "email": data.get("email", "").strip(),
        "address": data.get("address", "").strip(),
        "gst": data.get("gst", "").strip(),
    }})


def delete_supplier(supplier_id):
    get_db().suppliers.delete_one({"_id": _oid(supplier_id)})


# --- Settings and backup ---

DEFAULT_SETTINGS = {
    "company_name": "",
    "gst": "",
    "address": "",
    "phone": "",
    "email": "",
    "logo_path": "",
    "invoice_prefix": "INV",
    "default_tax": 0,
    "currency_symbol": "₹",
}


def get_settings():
    doc = get_db().settings.find_one({"key": "application"})
    return {**DEFAULT_SETTINGS, **(doc.get("value", {}) if doc else {})}


def save_settings(settings: dict):
    get_db().settings.update_one(
        {"key": "application"},
        {"$set": {"value": {**DEFAULT_SETTINGS, **settings}, "updated_at": now_iso()}},
        upsert=True,
    )


def export_database(file_path: str):
    database = get_db()
    payload = {}
    for name in database.list_collection_names():
        payload[name] = list(database[name].find())
    with open(file_path, "w", encoding="utf-8") as handle:
        handle.write(json_util.dumps(payload, indent=2))


def import_database(file_path: str):
    with open(file_path, "r", encoding="utf-8") as handle:
        payload = json_util.loads(handle.read())
    database = get_db()
    for name, documents in payload.items():
        database[name].delete_many({})
        if documents:
            database[name].insert_many(documents)
    _ensure_indexes(database)


# --- Dashboard stats ---

def get_dashboard_stats():
    db = get_db()
    total_products = db.products.count_documents({})
    stock_pipeline = [
        {"$group": {
            "_id": None,
            "total": {"$sum": {"$multiply": ["$stock_quantity", "$cost_price"]}},
        }},
    ]
    stock_result = list(db.products.aggregate(stock_pipeline))
    total_stock_value = stock_result[0]["total"] if stock_result else 0
    low_stock_count = len(get_low_stock_products())

    today = today_date()
    today_sales = list(db.sales.find({"created_at": {"$regex": f"^{today}"}}))
    today_revenue = sum(s.get("total", 0) for s in today_sales)
    today_sales_count = len(today_sales)

    all_sales = list(db.sales.find())
    total_revenue = sum(s.get("total", 0) for s in all_sales)
    total_sales_count = len(all_sales)

    recent = list(db.sales.find().sort("created_at", -1).limit(5))
    customer_ids = [s.get("customer_id") for s in recent if s.get("customer_id")]
    names = _customer_name_map(db, customer_ids)

    recent_sales = []
    for doc in recent:
        sale = _serialize_doc(doc)
        recent_sales.append({
            "id": sale["id"],
            "invoice_number": sale["invoice_number"],
            "total": sale["total"],
            "created_at": sale["created_at"],
            "customer_name": names.get(sale.get("customer_id")),
        })

    return {
        "total_products": total_products,
        "total_stock_value": total_stock_value,
        "low_stock_count": low_stock_count,
        "today_revenue": today_revenue,
        "today_sales_count": today_sales_count,
        "total_revenue": total_revenue,
        "total_sales_count": total_sales_count,
        "recent_sales": recent_sales,
        "low_stock_products": get_low_stock_products()[:5],
    }
