#!/usr/bin/env python3
"""Streamlit interface for Smart Billing and Inventory App."""

from datetime import date, datetime, timedelta
from pathlib import Path
import csv
import io

import streamlit as st
from bson import json_util

from database import db
from export_utils import (
    database_json, invoice_excel, invoice_pdf, report_excel, report_pdf,
)


st.set_page_config(
    page_title="Smart Billing and Inventory App",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  .stApp { background: #f1f5f9; }
  [data-testid="stSidebar"] { background: #1e293b; }
  [data-testid="stSidebar"] * { color: #f8fafc; }
  [data-testid="stMetric"] {
    background: white; border: 1px solid #e2e8f0; border-radius: 12px;
    padding: 16px;
  }
  div[data-testid="stForm"], div[data-testid="stExpander"] {
    background: white; border-radius: 12px;
  }
  .block-container { max-width: 1500px; padding-top: 1.5rem; }
  .invoice-banner {
    background:#292a33; color:white; border-radius:10px; padding:24px 28px;
    display:flex; justify-content:space-between; align-items:center;
    margin:4px 0 14px; min-height:82px;
  }
  .invoice-banner strong { color:#f2aa2e; font-size:34px; }
  .invoice-banner .banner-kicker { font-size:15px; font-weight:700; letter-spacing:.03em; }
  .invoice-banner .banner-subtitle { color:#d1d5db; font-size:13px; margin-top:5px; }
  .invoice-banner .bill-type { font-size:15px; font-style:italic; }
  .billing-section-label {
    display:inline-block; background:#f2aa2e; color:#292a33; font-weight:800;
    border-radius:4px; padding:5px 12px; margin:0 0 10px; letter-spacing:.02em;
  }
  .product-heading { font-size:16px; font-weight:800; color:#0f172a; }
  .product-help { color:#64748b; font-size:12px; margin-top:2px; }
  .product-table-header {
    display:grid; grid-template-columns:2.4fr .9fr .8fr 1fr .8fr .8fr 1.2fr .7fr;
    gap:10px; align-items:center; background:#f2aa2e; color:#292a33;
    border-radius:6px; padding:10px 14px; font-weight:800; margin:8px 0 5px;
  }
  .bill-summary-title { font-weight:800; color:#0f172a; margin-bottom:8px; }
  .summary-line {
    display:flex; justify-content:flex-end; gap:40px; color:#334155;
    padding:3px 4px; font-size:14px;
  }
  .summary-line span:first-child { min-width:130px; text-align:right; }
  .summary-line strong { min-width:140px; text-align:right; color:#0f172a; }
  .summary-total {
    display:flex; justify-content:flex-end; gap:40px; background:#f2aa2e;
    color:#292a33; border-radius:4px; padding:10px 14px; margin:8px 0 6px;
    font-size:20px; font-weight:800;
  }
  .summary-total span:first-child { min-width:160px; text-align:right; }
  .summary-total span:last-child { min-width:140px; text-align:right; }
  .balance-return { text-align:right; font-size:16px; font-weight:800; padding:6px 4px; }
  div[data-testid="stVerticalBlockBorderWrapper"] {
    background:#fff; border-color:#e2e8f0 !important; border-radius:10px;
  }
  .muted { color:#64748b; }
  .danger { color:#dc2626; }
</style>
""", unsafe_allow_html=True)


NAV_ITEMS = {
    "Billing": "🧾", "Inventory": "📦", "Customers": "👥",
    "Suppliers": "🚚", "Invoice Details": "📄", "Reports": "📈",
    "Settings": "⚙️",
}
UNITS = ["kg", "gram", "piece", "bunch", "dozen", "crate", "box", "bag", "litre"]
PAYMENTS = ["Cash", "UPI", "Card", "Bank Transfer"]


def money(value):
    return f"₹{float(value or 0):,.2f}"


def notify(message, kind="success"):
    st.session_state.flash = (kind, message)


def show_flash():
    flash = st.session_state.pop("flash", None)
    if flash:
        getattr(st, flash[0])(flash[1])


def rerun(page=None):
    if page:
        st.session_state.page = page
    st.rerun()


def reset_bill():
    settings = db.get_settings()
    st.session_state.bill_cart = []
    st.session_state.bill_invoice = db.generate_invoice_number()
    st.session_state.bill_date = date.today()
    st.session_state.bill_customer = "Walk-in Customer"
    st.session_state.bill_name = ""
    st.session_state.bill_phone = ""
    st.session_state.bill_email = ""
    st.session_state.bill_gst = ""
    st.session_state.bill_address = ""
    st.session_state.bill_payment = "Cash"
    st.session_state.bill_cash = 0.0
    st.session_state.default_tax = float(settings.get("default_tax", 0) or 0)


def init_state():
    st.session_state.setdefault("user", None)
    st.session_state.setdefault("page", "Billing")
    st.session_state.setdefault("current_report", None)
    st.session_state.setdefault("selected_invoice", None)
    st.session_state.setdefault("confirm_delete", None)
    if "bill_cart" not in st.session_state:
        reset_bill()


@st.cache_resource
def initialize_database():
    db.init_db()
    return True


def login():
    left, center, right = st.columns([1, 1.2, 1])
    with center:
        st.markdown("## Smart Billing and Inventory App")
        st.caption("Billing • Inventory • Sales")
        with st.form("login_form"):
            username = st.text_input("Username", value="admin")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign In", width="stretch")
        st.caption("Default: admin / admin123")
        if submitted:
            if not username or not password:
                st.error("Please enter username and password.")
            else:
                user = db.authenticate_user(username, password)
                if user:
                    st.session_state.user = user
                    rerun()
                else:
                    st.error("Invalid username or password.")


def sidebar():
    user = st.session_state.user
    with st.sidebar:
        st.markdown("## Smart Billing and Inventory App")
        st.caption("Billing • Inventory • Customers")
        st.markdown(f"👤 **{user.get('full_name') or user['username']}**")
        st.caption(user["username"])
        page = st.radio(
            "Navigation", list(NAV_ITEMS),
            index=list(NAV_ITEMS).index(st.session_state.page),
            format_func=lambda item: f"{NAV_ITEMS[item]}  {item}",
            label_visibility="collapsed",
        )
        if page != st.session_state.page:
            st.session_state.page = page
            st.rerun()
        st.divider()
        if st.button("Logout", width="stretch"):
            st.session_state.user = None
            reset_bill()
            rerun()


def page_title(title, subtitle):
    st.title(title)
    st.caption(subtitle)


def dashboard_strip():
    stats = db.get_dashboard_stats()
    cols = st.columns(4)
    cols[0].metric("Today's Revenue", money(stats["today_revenue"]),
                   f"{stats['today_sales_count']} sale(s)")
    cols[1].metric("Total Revenue", money(stats["total_revenue"]),
                   f"{stats['total_sales_count']} total sales")
    cols[2].metric("Products", stats["total_products"],
                   f"Stock value {money(stats['total_stock_value'])}")
    cols[3].metric("Low Stock Alerts", stats["low_stock_count"], "Items need restocking")


def bill_totals(items):
    subtotal = sum(float(i["quantity"]) * float(i["unit_price"]) for i in items)
    discount = sum(float(i.get("discount_amount", 0)) for i in items)
    tax = sum(float(i.get("tax_amount", 0)) for i in items)
    total = sum(float(i.get("amount", 0)) for i in items)
    return subtotal, discount, tax, total


def normalize_line(product, quantity, price, tax_rate, discount_rate):
    quantity = max(float(quantity), 0)
    price = max(float(price), 0)
    tax_rate = max(float(tax_rate), 0)
    discount_rate = min(max(float(discount_rate), 0), 100)
    subtotal = quantity * price
    discount_amount = subtotal * discount_rate / 100
    taxable = subtotal - discount_amount
    tax_amount = taxable * tax_rate / 100
    return {
        "product_id": product["id"], "product_name": product["name"],
        "quantity": quantity, "unit": product.get("unit", "kg"),
        "unit_price": price, "subtotal": subtotal, "tax_rate": tax_rate,
        "tax_amount": tax_amount, "discount_rate": discount_rate,
        "discount_amount": discount_amount, "amount": taxable + tax_amount,
        "max_stock": float(product["stock_quantity"]),
    }


def apply_customer_selection():
    selected = st.session_state.bill_customer
    if selected == "Walk-in Customer":
        for key in ["bill_name", "bill_phone", "bill_email", "bill_gst", "bill_address"]:
            st.session_state[key] = ""
        return
    customer = next((c for c in db.get_customers() if c["name"] == selected), None)
    if customer:
        st.session_state.bill_name = customer["name"]
        st.session_state.bill_phone = customer.get("phone", "")
        st.session_state.bill_email = customer.get("email", "")
        st.session_state.bill_gst = customer.get("gst", "")
        st.session_state.bill_address = customer.get("address", "")


def invoice_payload():
    subtotal, discount, tax, total = bill_totals(st.session_state.bill_cart)
    cash = float(st.session_state.bill_cash or 0)
    return {
        "invoice_number": st.session_state.bill_invoice,
        "invoice_date": str(st.session_state.bill_date),
        "customer_name": st.session_state.bill_name or "Walk-in Customer",
        "customer_phone": st.session_state.bill_phone,
        "customer_email": st.session_state.bill_email,
        "customer_gst": st.session_state.bill_gst,
        "customer_address": st.session_state.bill_address,
        "payment_method": st.session_state.bill_payment,
        "subtotal": subtotal, "discount": discount, "tax_amount": tax,
        "total": total, "cash_received": cash,
        "balance_return": max(cash - total, 0),
    }


def render_invoice(invoice, items):
    st.markdown(f"### INVOICE — {invoice['invoice_number']}")
    st.caption(f"Date: {invoice.get('invoice_date') or invoice.get('created_at', '')}")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Bill To**")
        st.write(invoice.get("customer_name") or "Walk-in Customer")
        for value in [
            invoice.get("customer_phone"), invoice.get("customer_email"),
            invoice.get("customer_address"),
            f"GST: {invoice.get('customer_gst')}" if invoice.get("customer_gst") else "",
        ]:
            if value:
                st.caption(value)
    with c2:
        st.markdown("**Payment**")
        st.write(invoice.get("payment_method", "Cash"))
    st.dataframe([{
        "Product": item["product_name"], "Qty": item["quantity"],
        "Unit": item.get("unit", "pcs"), "Price": money(item["unit_price"]),
        "Tax %": item.get("tax_rate", 0), "Disc %": item.get("discount_rate", 0),
        "Amount": money(item.get("amount", item.get("subtotal", 0))),
    } for item in items], width="stretch", hide_index=True)
    cols = st.columns(4)
    cols[0].metric("Subtotal", money(invoice["subtotal"]))
    cols[1].metric("Discount", money(invoice["discount"]))
    cols[2].metric("Tax", money(invoice["tax_amount"]))
    cols[3].metric("Total", money(invoice["total"]))


def billing_page():
    page_title("Billing", "Create, edit, export and print customer invoices")
    st.markdown("""
    <div class="invoice-banner">
      <div>
        <div class="banner-kicker">BILLING & INVENTORY</div>
        <div class="banner-subtitle">Professional customer invoice</div>
      </div>
      <div style="text-align:right">
        <div class="bill-type">CUSTOMER BILL</div>
        <strong>INVOICE</strong>
      </div>
    </div>
    """, unsafe_allow_html=True)
    customers = db.get_customers()
    names = ["Walk-in Customer"] + [c["name"] for c in customers]
    top_left, top_right = st.columns(2)
    with top_left:
        with st.container(border=True):
            st.markdown('<div class="billing-section-label">BILL TO</div>',
                        unsafe_allow_html=True)
            st.selectbox(
                "Saved customer", names, key="bill_customer",
                on_change=apply_customer_selection,
            )
            c1, c2 = st.columns(2)
            c1.text_input("Customer Name", key="bill_name")
            c2.text_input("Phone Number", key="bill_phone")
            c1.text_input("Email Address", key="bill_email")
            c2.text_input("GST Number", key="bill_gst")
            st.text_area("Address", key="bill_address", height=78)
            save_customer = st.checkbox("Save these customer details")
    with top_right:
        with st.container(border=True):
            st.markdown('<div class="billing-section-label">INVOICE DETAILS</div>',
                        unsafe_allow_html=True)
            st.text_input("Invoice #", key="bill_invoice")
            st.date_input("Invoice Date", key="bill_date")
            st.selectbox("Payment Mode", PAYMENTS, key="bill_payment")
            st.markdown("<div style='height:145px'></div>", unsafe_allow_html=True)

    products = [p for p in db.get_products() if float(p.get("stock_quantity", 0)) > 0]
    with st.container(border=True):
        heading_col, add_col = st.columns([5, 1.2])
        with heading_col:
            st.markdown(
                '<div class="product-heading">PRODUCT DETAILS</div>'
                '<div class="product-help">Select an item, then enter Qty and Price '
                'like an Excel sheet.</div>',
                unsafe_allow_html=True,
            )
        with add_col:
            add_panel = st.popover("+ Add Product Row", width="stretch")
        with add_panel:
            if not products:
                st.warning("Add a product with available stock in Inventory first.")
            else:
                product_map = {p["name"]: p for p in products}
                with st.form("add_bill_line", clear_on_submit=True):
                    product_name = st.selectbox("Product", list(product_map))
                    product = product_map[product_name]
                    st.caption(
                        f"Available: {float(product['stock_quantity']):g} "
                        f"{product.get('unit', 'kg')}"
                    )
                    quantity = st.number_input("Quantity", min_value=0.01, value=1.0)
                    price = st.number_input(
                        "Price", min_value=0.0, value=float(product["selling_price"])
                    )
                    c1, c2 = st.columns(2)
                    tax_rate = c1.number_input(
                        "Tax %", min_value=0.0, value=float(st.session_state.default_tax)
                    )
                    discount_rate = c2.number_input(
                        "Discount %", min_value=0.0, max_value=100.0, value=0.0
                    )
                    add = st.form_submit_button("Add to Bill", width="stretch")
                if add:
                    used = sum(
                        i["quantity"] for i in st.session_state.bill_cart
                        if i["product_id"] == product["id"]
                    )
                    if used + quantity > float(product["stock_quantity"]):
                        st.error(f"Only {float(product['stock_quantity']):g} is available.")
                    else:
                        st.session_state.bill_cart.append(
                            normalize_line(product, quantity, price, tax_rate, discount_rate)
                        )
                        rerun()

        st.markdown("""
        <div class="product-table-header">
          <span>Product</span><span>Stock</span><span>Qty</span><span>Price</span>
          <span>Tax %</span><span>Disc %</span><span>Amount</span><span></span>
        </div>
        """, unsafe_allow_html=True)

        if not st.session_state.bill_cart:
            st.info("Click “+ Add Product Row” to choose and add a product.")

        for index, item in enumerate(list(st.session_state.bill_cart)):
            with st.form(f"edit_line_{index}"):
                cols = st.columns([2.4, .9, .8, 1, .8, .8, 1.2, .7])
                cols[0].markdown(f"**{item['product_name']}**  \n"
                                 f"<span class='muted'>{item.get('unit', 'kg')}</span>",
                                 unsafe_allow_html=True)
                cols[1].markdown(
                    f"{item['max_stock']:g}  \n"
                    f"<span class='muted'>{item.get('unit', 'kg')}</span>",
                    unsafe_allow_html=True,
                )
                quantity = cols[2].number_input(
                    "Qty", min_value=0.0, max_value=float(item["max_stock"]),
                    value=float(item["quantity"]), key=f"qty_{index}",
                    label_visibility="collapsed",
                )
                price = cols[3].number_input(
                    "Price", min_value=0.0, value=float(item["unit_price"]),
                    key=f"price_{index}", label_visibility="collapsed",
                )
                tax_rate = cols[4].number_input(
                    "Tax %", min_value=0.0, value=float(item.get("tax_rate", 0)),
                    key=f"tax_{index}", label_visibility="collapsed",
                )
                discount_rate = cols[5].number_input(
                    "Disc %", min_value=0.0, max_value=100.0,
                    value=float(item.get("discount_rate", 0)), key=f"disc_{index}",
                    label_visibility="collapsed",
                )
                cols[6].markdown(f"**{money(item['amount'])}**")
                update = cols[7].form_submit_button("✓", help="Update row")
                remove = cols[7].form_submit_button("✕", help="Remove row")
            if update:
                product = db.get_product(item["product_id"])
                st.session_state.bill_cart[index] = normalize_line(
                    product, quantity, price, tax_rate, discount_rate
                )
                rerun()
            if remove:
                st.session_state.bill_cart.pop(index)
                rerun()

        invoice = invoice_payload()
        st.divider()
        with st.container(border=True):
            st.markdown('<div class="bill-summary-title">BILL SUMMARY</div>',
                        unsafe_allow_html=True)
            st.markdown(
                f'<div class="summary-line"><span>Subtotal:</span>'
                f'<strong>{money(invoice["subtotal"])}</strong></div>'
                f'<div class="summary-line"><span>Discount:</span>'
                f'<strong>{money(invoice["discount"])}</strong></div>'
                f'<div class="summary-line"><span>Tax:</span>'
                f'<strong>{money(invoice["tax_amount"])}</strong></div>'
                f'<div class="summary-total"><span>Total Amount:</span>'
                f'<span>{money(invoice["total"])}</span></div>',
                unsafe_allow_html=True,
            )
            cash_label, cash_input = st.columns([5, 1.35])
            cash_label.markdown("<div style='text-align:right;padding-top:9px'>"
                                "<b>Cash Received</b></div>", unsafe_allow_html=True)
            cash_input.number_input(
                "Cash Received", min_value=0.0, key="bill_cash",
                label_visibility="collapsed",
            )
            invoice = invoice_payload()
            st.markdown(
                f'<div class="balance-return">Balance Return: '
                f'{money(invoice["balance_return"])}</div>',
                unsafe_allow_html=True,
            )

    actions = st.columns(5)
    preview = actions[0].button("Generate Invoice", width="stretch")
    save = actions[1].button("Save Bill", type="primary", width="stretch")
    if st.session_state.bill_cart:
        actions[2].download_button(
            "Download PDF", invoice_pdf(invoice, st.session_state.bill_cart),
            file_name=f"invoice_{invoice['invoice_number']}.pdf",
            mime="application/pdf", width="stretch",
        )
        actions[3].download_button(
            "Download Excel", invoice_excel(invoice, st.session_state.bill_cart),
            file_name=f"invoice_{invoice['invoice_number']}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
        )
        actions[4].download_button(
            "Print Bill", invoice_pdf(invoice, st.session_state.bill_cart),
            file_name=f"print_{invoice['invoice_number']}.pdf",
            mime="application/pdf", width="stretch",
            help="Download the print-ready PDF and print it from your browser.",
        )
    if preview:
        if st.session_state.bill_cart:
            render_invoice(invoice, st.session_state.bill_cart)
        else:
            st.warning("Please add at least one product.")
    if save:
        if not st.session_state.bill_cart:
            st.warning("Please add at least one product before saving the bill.")
            return
        customer_ids = {c["name"]: c["id"] for c in customers}
        customer_id = customer_ids.get(st.session_state.bill_customer)
        if save_customer and invoice["customer_name"] != "Walk-in Customer" and not customer_id:
            customer_id = db.add_customer({
                "name": invoice["customer_name"], "phone": invoice["customer_phone"],
                "email": invoice["customer_email"], "gst": invoice["customer_gst"],
                "address": invoice["customer_address"],
            })
        sale_data = {
            **invoice, "customer_id": customer_id,
            "tax_rate": 0, "invoice_number": invoice["invoice_number"],
        }
        try:
            sale_id = db.create_sale(sale_data, st.session_state.bill_cart)
            export_dir = Path(__file__).parent / "exports"
            export_dir.mkdir(exist_ok=True)
            path = export_dir / f"bill_{datetime.now():%Y%m%d_%H%M%S}.csv"
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Invoice", invoice["invoice_number"]])
                writer.writerow(["Customer", invoice["customer_name"]])
                writer.writerow([])
                writer.writerow(["Product", "Qty", "Price", "Tax %", "Disc %", "Amount"])
                for item in st.session_state.bill_cart:
                    writer.writerow([
                        item["product_name"], item["quantity"], item["unit_price"],
                        item["tax_rate"], item["discount_rate"], item["amount"],
                    ])
                writer.writerow(["Grand Total", invoice["total"]])
            st.session_state.selected_invoice = sale_id
            reset_bill()
            notify(f"Bill saved successfully. Invoice: {invoice['invoice_number']}")
            rerun("Invoice Details")
        except Exception as exc:
            st.error(f"Unable to save bill: {exc}")


def product_form(product=None):
    prefix = f"product_{product['id']}" if product else "new_product"
    with st.form(prefix):
        name = st.text_input("Product Name *", value=(product or {}).get("name", ""))
        cols = st.columns(2)
        cost = cols[0].number_input(
            "Purchased Price per Unit *", min_value=0.0,
            value=float((product or {}).get("cost_price", 0))
        )
        price = cols[1].number_input(
            "Selling Price per Unit *", min_value=0.0,
            value=float((product or {}).get("selling_price", 0))
        )
        stock = cols[0].number_input(
            "Current Stock *", min_value=0.0,
            value=float((product or {}).get("stock_quantity", 0))
        )
        minimum = cols[1].number_input(
            "Low Stock Alert Quantity", min_value=0.0,
            value=float((product or {}).get("min_stock_level", 5))
        )
        unit_value = (product or {}).get("unit", "kg")
        unit = st.selectbox("Unit *", UNITS, index=UNITS.index(unit_value) if unit_value in UNITS else 0)
        description = st.text_area("Description", value=(product or {}).get("description", ""))
        submitted = st.form_submit_button(
            "Update Product" if product else "Add Product", width="stretch"
        )
    if submitted:
        if not name.strip():
            st.error("Product Name is required.")
        else:
            data = {
                "name": name.strip(), "category_id": (product or {}).get("category_id"),
                "cost_price": cost, "selling_price": price, "stock_quantity": stock,
                "min_stock_level": minimum, "unit": unit, "description": description,
            }
            if product:
                db.update_product(product["id"], data)
            else:
                db.add_product(data)
            notify("Product saved successfully.")
            rerun()


def inventory_page():
    page_title("Inventory", "Manage products and stock levels")
    search = st.text_input("Search products", placeholder="Search products...")
    products = db.get_products(search)
    st.dataframe([{
        "Product Name": p["name"], "Purchase Price / Unit": money(p["cost_price"]),
        "Selling Price / Unit": money(p["selling_price"]), "Stock": p["stock_quantity"],
        "Unit": p.get("unit", "kg"), "Low Stock Alert": p["min_stock_level"],
        "Status": "Low stock" if p["stock_quantity"] <= p["min_stock_level"] else "In stock",
    } for p in products], width="stretch", hide_index=True)
    tabs = st.tabs(["Add Product", "Edit Product", "Adjust Stock", "Delete Product"])
    with tabs[0]:
        product_form()
    with tabs[1]:
        if products:
            selected = st.selectbox("Select product to edit", products, format_func=lambda p: p["name"])
            product_form(selected)
        else:
            st.info("No products found.")
    with tabs[2]:
        if products:
            selected = st.selectbox(
                "Select product", products, format_func=lambda p: p["name"], key="stock_product"
            )
            with st.form("adjust_stock"):
                st.write(f"Current stock: **{selected['stock_quantity']:g}**")
                change = st.number_input("Quantity change (+/-)", value=0.0)
                submit = st.form_submit_button("Apply")
            if submit:
                db.adjust_stock(selected["id"], change)
                notify("Stock adjusted.")
                rerun()
    with tabs[3]:
        if products:
            selected = st.selectbox(
                "Select product to delete", products, format_func=lambda p: p["name"],
                key="delete_product"
            )
            if st.button("Delete Product", type="primary"):
                db.delete_product(selected["id"])
                notify("Product deleted.")
                rerun()


def contact_form(kind, record=None):
    singular = kind[:-1].capitalize()
    key = f"{kind}_{(record or {}).get('id', 'new')}"
    with st.form(key):
        name = st.text_input(f"{singular} Name *", value=(record or {}).get("name", ""))
        address = st.text_area("Address", value=(record or {}).get("address", ""))
        cols = st.columns(2)
        phone = cols[0].text_input("Phone Number", value=(record or {}).get("phone", ""))
        email = cols[1].text_input("Email", value=(record or {}).get("email", ""))
        gst = st.text_input("GST Number", value=(record or {}).get("gst", ""))
        submit = st.form_submit_button(f"Save {singular}", width="stretch")
    if submit:
        if not name.strip():
            st.error(f"{singular} Name is required.")
            return
        data = {"name": name, "address": address, "phone": phone, "email": email, "gst": gst}
        if kind == "customers":
            db.update_customer(record["id"], data) if record else db.add_customer(data)
        else:
            db.update_supplier(record["id"], data) if record else db.add_supplier(data)
        notify(f"{singular} saved successfully.")
        rerun()


def contacts_page(kind):
    singular = kind[:-1].capitalize()
    page_title(
        singular + "s" if kind == "customers" else "Supplier Management",
        f"Manage {singular.lower()} contact, address, and GST details",
    )
    search = st.text_input(f"Search {kind}")
    records = db.get_customers(search) if kind == "customers" else db.get_suppliers(search)
    st.dataframe([{
        f"{singular} Name": r["name"], "Phone": r.get("phone") or "—",
        "Email": r.get("email") or "—", "Address": r.get("address") or "—",
        "GST": r.get("gst") or "—",
    } for r in records], width="stretch", hide_index=True)
    tabs = st.tabs([f"Add {singular}", f"Edit {singular}", f"Delete {singular}"])
    with tabs[0]:
        contact_form(kind)
    with tabs[1]:
        if records:
            selected = st.selectbox(
                f"Select {singular.lower()}", records, format_func=lambda r: r["name"],
                key=f"edit_{kind}"
            )
            contact_form(kind, selected)
    with tabs[2]:
        if records:
            selected = st.selectbox(
                f"Select {singular.lower()} to delete", records,
                format_func=lambda r: r["name"], key=f"delete_{kind}"
            )
            if st.button(f"Delete {singular}", type="primary"):
                (db.delete_customer if kind == "customers" else db.delete_supplier)(selected["id"])
                notify(f"{singular} deleted.")
                rerun()


def invoices_page():
    page_title("Invoice Details", "View saved invoices and sales history")
    search = st.text_input("Search by invoice or customer")
    sales = db.get_sales(search)
    st.dataframe([{
        "Invoice #": s["invoice_number"], "Customer": s.get("customer_name") or "Walk-in",
        "Total": money(s["total"]), "Payment": s["payment_method"],
        "Date": s["created_at"][:16],
    } for s in sales], width="stretch", hide_index=True)
    if not sales:
        st.info("No invoices found.")
        return
    default = 0
    highlighted = st.session_state.pop("selected_invoice", None)
    if highlighted:
        default = next((i for i, s in enumerate(sales) if s["id"] == highlighted), 0)
    selected = st.selectbox(
        "View invoice", sales, index=default,
        format_func=lambda s: f"{s['invoice_number']} — {s.get('customer_name') or 'Walk-in'}"
    )
    sale = db.get_sale(selected["id"])
    invoice = {
        **sale, "invoice_date": sale["created_at"][:10],
        "discount": sale.get("discount", 0),
    }
    render_invoice(invoice, sale["items"])
    cols = st.columns(2)
    cols[0].download_button(
        "Download Invoice PDF", invoice_pdf(invoice, sale["items"]),
        file_name=f"{sale['invoice_number']}.pdf", mime="application/pdf",
        width="stretch",
    )
    cols[1].download_button(
        "Download Invoice Excel", invoice_excel(invoice, sale["items"]),
        file_name=f"{sale['invoice_number']}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
    )


def period_dates(period):
    today = date.today()
    if period == "Daily":
        return today, today
    if period == "Weekly":
        return today - timedelta(days=today.weekday()), today
    if period == "Monthly":
        return today.replace(day=1), today
    if period == "Yearly":
        return today.replace(month=1, day=1), today
    return today, today


def render_report(report):
    st.subheader(f"{report['report_type']} — {report['period_label']}")
    if report["report_type"] == "Sales Report":
        cards = st.columns(4)
        cards[0].metric("Revenue", money(report["revenue"]))
        cards[1].metric("Profit", money(report["profit"]))
        cards[2].metric("Tax Collected", money(report["tax_collected"]))
        cards[3].metric("Invoices", report["sales_count"])
        st.markdown("#### Product Wise Sales")
        st.dataframe(report["product_sales"], width="stretch", hide_index=True)
    elif report["report_type"] == "Inventory Report":
        cards = st.columns(4)
        cards[0].metric("Current Stock", f"{report['total_units']:g}")
        cards[1].metric("Low Stock", len(report["low_stock"]))
        cards[2].metric("Inventory Value", money(report["inventory_value"]))
        cards[3].metric("Out of Stock", len(report["out_of_stock"]))
        st.markdown("#### Current Stock")
        st.dataframe(report["current_stock"], width="stretch", hide_index=True)
        st.markdown("#### Low Stock Products")
        st.dataframe(report["low_stock"], width="stretch", hide_index=True)
        st.markdown("#### Out of Stock Products")
        st.dataframe(report["out_of_stock"], width="stretch", hide_index=True)
    else:
        cards = st.columns(4)
        for col, method in zip(cards, PAYMENTS):
            col.metric(method, money(report["collections"].get(method, 0)))
        st.dataframe([{
            "Opening": money(report["opening_balance"]),
            "Sales": money(report["sales_collection"]),
            "Expenses": money(report["expenses"]),
            "Closing": money(report["closing_balance"]),
        }], width="stretch", hide_index=True)


def reports_page():
    page_title("Reports", "Generate professional sales, inventory and payment reports")
    with st.form("report_controls"):
        cols = st.columns([1.3, 1, 1, 1])
        kind = cols[0].selectbox(
            "Report", ["Sales Report", "Inventory Report", "Payment Report"]
        )
        period = cols[1].selectbox(
            "Period", ["Daily", "Weekly", "Monthly", "Yearly", "Custom Date"],
            index=2, disabled=kind == "Inventory Report",
        )
        suggested_start, suggested_end = period_dates(period)
        start = cols[2].date_input(
            "Start", suggested_start, disabled=kind == "Inventory Report"
        )
        end = cols[3].date_input(
            "End", suggested_end, disabled=kind == "Inventory Report"
        )
        opening = expenses = 0.0
        if kind == "Payment Report":
            cash = st.columns(2)
            opening = cash[0].number_input("Opening Balance", value=0.0)
            expenses = cash[1].number_input("Expenses", value=0.0)
        generate = st.form_submit_button("Generate", width="stretch")
    if generate:
        if kind == "Inventory Report":
            report = db.get_inventory_report()
        elif kind == "Sales Report":
            report = db.get_sales_report(str(start), str(end))
        else:
            report = db.get_payment_report(str(start), str(end), opening, expenses)
        st.session_state.current_report = report
    report = st.session_state.current_report
    if report:
        render_report(report)
        cols = st.columns(2)
        name = report["report_type"].lower().replace(" ", "_")
        cols[0].download_button(
            "Download Excel", report_excel(report), file_name=f"{name}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
        )
        cols[1].download_button(
            "Download PDF", report_pdf(report), file_name=f"{name}.pdf",
            mime="application/pdf", width="stretch",
        )
    else:
        st.info("Choose a report and click Generate.")


def settings_page():
    page_title("Settings", "Company profile, invoice and backup settings")
    settings = db.get_settings()
    with st.form("settings_form"):
        st.subheader("Company Profile")
        company_name = st.text_input("Company Name", value=settings.get("company_name", ""))
        gst = st.text_input("GST Number", value=settings.get("gst", ""))
        address = st.text_area("Address", value=settings.get("address", ""))
        cols = st.columns(2)
        phone = cols[0].text_input("Phone Number", value=settings.get("phone", ""))
        email = cols[1].text_input("Email", value=settings.get("email", ""))
        logo_path = st.text_input("Logo path", value=settings.get("logo_path", ""))
        st.subheader("Invoice Settings")
        cols = st.columns(3)
        prefix = cols[0].text_input("Invoice Prefix", value=settings.get("invoice_prefix", "INV"))
        tax = cols[1].number_input(
            "Tax Settings (%)", min_value=0.0,
            value=float(settings.get("default_tax", 0))
        )
        currency = cols[2].text_input(
            "Currency Symbol", value=settings.get("currency_symbol", "₹")
        )
        save = st.form_submit_button("Save Settings", width="stretch")
    if save:
        db.save_settings({
            "company_name": company_name, "gst": gst, "address": address,
            "phone": phone, "email": email, "logo_path": logo_path,
            "invoice_prefix": prefix, "default_tax": tax,
            "currency_symbol": currency,
        })
        st.session_state.default_tax = tax
        notify("Settings saved successfully.")
        rerun()
    st.subheader("Backup Settings")
    cols = st.columns(2)
    cols[0].download_button(
        "Export Database", database_json(db.get_db()),
        file_name="bizmanager_backup.json", mime="application/json",
        width="stretch",
    )
    upload = cols[1].file_uploader("Import Database", type=["json"])
    if upload and st.button("Restore uploaded backup", type="primary"):
        try:
            payload = json_util.loads(upload.getvalue().decode("utf-8"))
            database = db.get_db()
            for name, documents in payload.items():
                database[name].delete_many({})
                if documents:
                    database[name].insert_many(documents)
            db._ensure_indexes(database)
            notify("Database imported successfully.")
            rerun()
        except Exception as exc:
            st.error(f"Import failed: {exc}")


def main():
    try:
        initialize_database()
    except Exception as exc:
        st.error(
            "Could not connect to MongoDB. Start MongoDB or set MONGO_URI, then reload."
        )
        st.exception(exc)
        return
    init_state()
    if not st.session_state.user:
        login()
        return
    sidebar()
    show_flash()
    pages = {
        "Billing": billing_page, "Inventory": inventory_page,
        "Customers": lambda: contacts_page("customers"),
        "Suppliers": lambda: contacts_page("suppliers"),
        "Invoice Details": invoices_page, "Reports": reports_page,
        "Settings": settings_page,
    }
    pages[st.session_state.page]()


if __name__ == "__main__":
    main()
