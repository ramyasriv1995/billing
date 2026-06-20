import customtkinter as ctk

from database import db
from .components import format_currency, page_header, styled_treeview
from .theme import COLORS, FONT_BODY, FONT_HEADING, FONT_SMALL


class SalesFrame(ctk.CTkFrame):
    def __init__(self, parent, on_sale_complete=None):
        super().__init__(parent, fg_color=COLORS["bg"])
        self.on_sale_complete = on_sale_complete
        self.cart = []
        self.grid_columnconfigure(0, weight=2)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build()

    def refresh(self):
        self.cart.clear()
        for widget in self.winfo_children():
            widget.destroy()
        self._build()

    def _build(self):
        page_header(self, "Sales", "Add products to cart and complete checkout").grid(
            row=0, column=0, columnspan=2, sticky="ew", padx=24, pady=(24, 12)
        )

        left = ctk.CTkFrame(self, fg_color=COLORS["card"], corner_radius=12)
        left.grid(row=1, column=0, sticky="nsew", padx=(24, 8), pady=(0, 24))
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(1, weight=1)

        top_left = ctk.CTkFrame(left, fg_color="transparent")
        top_left.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        top_left.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(top_left, text="Products", font=FONT_HEADING).grid(
            row=0, column=0, sticky="w", padx=(0, 12)
        )

        self.product_search = ctk.StringVar()
        self.product_search.trace_add("write", lambda *_: self._load_product_list())
        ctk.CTkEntry(
            top_left, placeholder_text="Search products...", textvariable=self.product_search
        ).grid(row=0, column=1, sticky="ew")

        self.product_list = ctk.CTkScrollableFrame(left, fg_color=COLORS["bg"])
        self.product_list.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

        right = ctk.CTkFrame(self, fg_color=COLORS["card"], corner_radius=12)
        right.grid(row=1, column=1, sticky="nsew", padx=(8, 24), pady=(0, 24))
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(right, text="Cart", font=FONT_HEADING).grid(
            row=0, column=0, sticky="w", padx=16, pady=(16, 8)
        )

        self.cart_frame = ctk.CTkScrollableFrame(right, fg_color=COLORS["bg"])
        self.cart_frame.grid(row=2, column=0, sticky="nsew", padx=12, pady=4)

        totals = ctk.CTkFrame(right, fg_color="transparent")
        totals.grid(row=3, column=0, sticky="ew", padx=16, pady=8)
        totals.grid_columnconfigure(1, weight=1)

        self.subtotal_label = ctk.CTkLabel(totals, text="Subtotal: ₹0.00", font=FONT_BODY)
        self.subtotal_label.grid(row=0, column=0, columnspan=2, sticky="w", pady=2)

        ctk.CTkLabel(totals, text="Tax %:", font=FONT_SMALL).grid(row=1, column=0, sticky="w")
        self.tax_entry = ctk.CTkEntry(totals, width=60, placeholder_text="0")
        self.tax_entry.insert(0, "0")
        self.tax_entry.grid(row=1, column=1, sticky="w", padx=8)

        ctk.CTkLabel(totals, text="Discount (₹):", font=FONT_SMALL).grid(row=2, column=0, sticky="w", pady=4)
        self.discount_entry = ctk.CTkEntry(totals, width=60, placeholder_text="0")
        self.discount_entry.insert(0, "0")
        self.discount_entry.grid(row=2, column=1, sticky="w", padx=8, pady=4)

        self.total_label = ctk.CTkLabel(
            totals, text="Total: ₹0.00", font=("Helvetica", 18, "bold"), text_color=COLORS["primary"]
        )
        self.total_label.grid(row=3, column=0, columnspan=2, sticky="w", pady=(8, 4))

        ctk.CTkLabel(totals, text="Payment:", font=FONT_SMALL).grid(row=4, column=0, sticky="w")
        self.payment_method = ctk.CTkComboBox(
            totals, values=["Cash", "Card", "UPI", "Bank Transfer"], width=140
        )
        self.payment_method.set("Cash")
        self.payment_method.grid(row=4, column=1, sticky="w", padx=8)

        ctk.CTkLabel(totals, text="Customer:", font=FONT_SMALL).grid(row=5, column=0, sticky="w", pady=4)
        cust_row = ctk.CTkFrame(totals, fg_color="transparent")
        cust_row.grid(row=5, column=1, sticky="w", padx=8, pady=4)
        customers = db.get_customers()
        cust_names = ["Walk-in Customer"] + [c["name"] for c in customers]
        self.customer_combo = ctk.CTkComboBox(cust_row, values=cust_names, width=150)
        self.customer_combo.set("Walk-in Customer")
        self.customer_combo.pack(side="left")
        self._customers = {c["name"]: c["id"] for c in customers}
        ctk.CTkButton(
            cust_row, text="+", width=32, height=28,
            fg_color=COLORS["primary"],
            command=self._open_add_customer,
        ).pack(side="left", padx=(6, 0))

        ctk.CTkButton(
            right, text="Complete Sale", height=40,
            fg_color=COLORS["success"], hover_color="#15803D",
            command=self._complete_sale,
        ).grid(row=4, column=0, sticky="ew", padx=16, pady=(4, 16))

        self.tax_entry.bind("<KeyRelease>", lambda e: self._update_totals())
        self.discount_entry.bind("<KeyRelease>", lambda e: self._update_totals())

        self._load_product_list()
        self._render_cart()

    def _load_product_list(self):
        for w in self.product_list.winfo_children():
            w.destroy()
        search = self.product_search.get() if hasattr(self, "product_search") else ""
        products = db.get_products(search)

        header = ctk.CTkFrame(self.product_list, fg_color=COLORS["bg"])
        header.pack(fill="x", padx=4, pady=(0, 4))
        header.grid_columnconfigure(0, weight=2)
        header.grid_columnconfigure(1, weight=1)
        header.grid_columnconfigure(2, weight=1)
        header.grid_columnconfigure(3, weight=0)

        ctk.CTkLabel(header, text="Product", font=FONT_SMALL, text_color=COLORS["text_muted"]).grid(
            row=0, column=0, sticky="w", padx=8, pady=(8, 4)
        )
        ctk.CTkLabel(header, text="Price", font=FONT_SMALL, text_color=COLORS["text_muted"]).grid(
            row=0, column=1, sticky="w", padx=8, pady=(8, 4)
        )
        ctk.CTkLabel(header, text="Stock", font=FONT_SMALL, text_color=COLORS["text_muted"]).grid(
            row=0, column=2, sticky="w", padx=8, pady=(8, 4)
        )

        for p in products:
            if p["stock_quantity"] <= 0:
                continue
            row = ctk.CTkFrame(self.product_list, fg_color=COLORS["card"], corner_radius=8)
            row.pack(fill="x", pady=3, padx=4)
            row.grid_columnconfigure(0, weight=2)
            row.grid_columnconfigure(1, weight=1)
            row.grid_columnconfigure(2, weight=1)
            row.grid_columnconfigure(3, weight=0)

            ctk.CTkLabel(row, text=p["name"], font=FONT_SMALL, anchor="w").grid(
                row=0, column=0, sticky="ew", padx=10, pady=8
            )
            ctk.CTkLabel(
                row, text=format_currency(p["selling_price"]), font=FONT_SMALL, anchor="w"
            ).grid(row=0, column=1, sticky="ew", padx=10, pady=8)
            ctk.CTkLabel(
                row, text=str(p["stock_quantity"]), font=FONT_SMALL, anchor="w"
            ).grid(row=0, column=2, sticky="ew", padx=10, pady=8)
            ctk.CTkButton(
                row, text="Add", width=60, height=28,
                fg_color=COLORS["primary"],
                command=lambda prod=p: self._add_to_cart(prod),
            ).grid(row=0, column=3, padx=8, pady=6)

    def _add_to_cart(self, product):
        for item in self.cart:
            if item["product_id"] == product["id"]:
                if item["quantity"] < product["stock_quantity"]:
                    item["quantity"] += 1
                    item["subtotal"] = item["quantity"] * item["unit_price"]
                self._render_cart()
                return
        self.cart.append({
            "product_id": product["id"],
            "product_name": product["name"],
            "quantity": 1,
            "unit": product.get("unit", "pcs"),
            "unit_price": product["selling_price"],
            "subtotal": product["selling_price"],
            "max_stock": product["stock_quantity"],
        })
        self._render_cart()

    def _render_cart(self):
        for w in self.cart_frame.winfo_children():
            w.destroy()

        if not self.cart:
            ctk.CTkLabel(
                self.cart_frame, text="Cart is empty", text_color=COLORS["text_muted"]
            ).pack(pady=20)
            self._update_totals()
            return

        for i, item in enumerate(self.cart):
            row = ctk.CTkFrame(self.cart_frame, fg_color=COLORS["card"], corner_radius=8)
            row.pack(fill="x", pady=3, padx=4)
            row.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                row, text=item["product_name"], font=FONT_SMALL, anchor="w"
            ).grid(row=0, column=0, columnspan=3, sticky="w", padx=8, pady=(6, 0))

            def dec(idx=i):
                if self.cart[idx]["quantity"] > 1:
                    self.cart[idx]["quantity"] -= 1
                    self.cart[idx]["subtotal"] = self.cart[idx]["quantity"] * self.cart[idx]["unit_price"]
                else:
                    self.cart.pop(idx)
                self._render_cart()

            def inc(idx=i):
                if self.cart[idx]["quantity"] < self.cart[idx]["max_stock"]:
                    self.cart[idx]["quantity"] += 1
                    self.cart[idx]["subtotal"] = self.cart[idx]["quantity"] * self.cart[idx]["unit_price"]
                    self._render_cart()

            ctk.CTkButton(row, text="−", width=30, height=28, command=dec).grid(row=1, column=0, padx=4, pady=6)
            ctk.CTkLabel(row, text=str(item["quantity"]), font=FONT_BODY).grid(row=1, column=1, padx=4)
            ctk.CTkButton(row, text="+", width=30, height=28, command=inc).grid(row=1, column=2, padx=4, pady=6)
            ctk.CTkLabel(
                row, text=format_currency(item["subtotal"]), font=FONT_BODY
            ).grid(row=1, column=3, padx=8, pady=6)

        self._update_totals()

    def _calc_totals(self):
        subtotal = sum(i["subtotal"] for i in self.cart)
        try:
            tax_rate = float(self.tax_entry.get() or 0)
        except ValueError:
            tax_rate = 0
        try:
            discount = float(self.discount_entry.get() or 0)
        except ValueError:
            discount = 0
        tax_amount = subtotal * (tax_rate / 100)
        total = max(subtotal + tax_amount - discount, 0)
        return subtotal, tax_rate, tax_amount, discount, total

    def _update_totals(self):
        subtotal, _, tax_amount, discount, total = self._calc_totals()
        self.subtotal_label.configure(
            text=f"Subtotal: {format_currency(subtotal)}  |  Tax: {format_currency(tax_amount)}  |  Discount: {format_currency(discount)}"
        )
        self.total_label.configure(text=f"Total: {format_currency(total)}")

    def _complete_sale(self):
        if not self.cart:
            return
        subtotal, tax_rate, tax_amount, discount, total = self._calc_totals()
        cust_name = self.customer_combo.get()
        customer_id = self._customers.get(cust_name)

        sale_data = {
            "invoice_number": db.generate_invoice_number(),
            "customer_id": customer_id,
            "subtotal": subtotal,
            "tax_rate": tax_rate,
            "tax_amount": tax_amount,
            "discount": discount,
            "total": total,
            "payment_method": self.payment_method.get(),
        }
        try:
            sale_id = db.create_sale(sale_data, self.cart)
        except ValueError as exc:
            dialog = ctk.CTkToplevel(self)
            dialog.title("Stock changed")
            dialog.geometry("420x180")
            dialog.transient(self.winfo_toplevel())
            dialog.grab_set()
            ctk.CTkLabel(
                dialog, text=str(exc), font=FONT_BODY, wraplength=360
            ).pack(padx=24, pady=(30, 18))
            ctk.CTkButton(dialog, text="OK", command=dialog.destroy).pack()
            self._load_product_list()
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title("Sale Complete")
        dialog.geometry("400x200")
        dialog.resizable(False, False)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text=f"Sale completed!\nInvoice: {sale_data['invoice_number']}\nTotal: {format_currency(total)}",
            font=FONT_BODY,
        ).pack(pady=30)

        def close_and_refresh():
            dialog.destroy()
            self.cart.clear()
            self.refresh()
            if self.on_sale_complete:
                self.on_sale_complete(sale_id)

        ctk.CTkButton(
            dialog, text="OK", width=100, fg_color=COLORS["success"], command=close_and_refresh
        ).pack()

    def _open_add_customer(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Add Customer")
        dialog.geometry("420x360")
        dialog.resizable(False, False)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        fields = {}
        for i, (key, label) in enumerate([
            ("name", "Customer Name *"),
            ("address", "Customer Address"),
            ("gst", "GST Number"),
        ]):
            ctk.CTkLabel(dialog, text=label, font=FONT_BODY).grid(
                row=i, column=0, sticky="w", padx=24, pady=(12 if i == 0 else 6, 2)
            )
            if key == "address":
                widget = ctk.CTkTextbox(dialog, width=340, height=70)
            else:
                widget = ctk.CTkEntry(dialog, width=340)
            widget.grid(row=i, column=0, padx=24, pady=(0, 4))
            fields[key] = widget

        def save():
            name = fields["name"].get().strip()
            if not name:
                return
            db.add_customer({
                "name": name,
                "address": fields["address"].get("1.0", "end").strip()
                if hasattr(fields["address"], "get")
                else "",
                "gst": fields["gst"].get().strip(),
            })
            dialog.destroy()
            customers = db.get_customers()
            cust_names = ["Walk-in Customer"] + [c["name"] for c in customers]
            self.customer_combo.configure(values=cust_names)
            self.customer_combo.set(name)
            self._customers = {c["name"]: c["id"] for c in customers}

        ctk.CTkButton(
            dialog, text="Save", width=120, fg_color=COLORS["primary"], command=save
        ).grid(row=4, column=0, pady=20)
