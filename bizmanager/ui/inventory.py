import customtkinter as ctk

from database import db
from .components import confirm_dialog, format_currency, page_header, styled_treeview
from .theme import COLORS, FONT_BODY, FONT_HEADING, FONT_SMALL


class InventoryFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color=COLORS["bg"])
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self._build()

    def refresh(self):
        for widget in self.winfo_children():
            widget.destroy()
        self._build()

    def _build(self):
        header_row = ctk.CTkFrame(self, fg_color="transparent")
        header_row.grid(row=0, column=0, sticky="ew", padx=24, pady=(24, 8))
        header_row.grid_columnconfigure(0, weight=1)

        page_header(header_row, "Inventory", "Manage products and stock levels").grid(
            row=0, column=0, sticky="w"
        )

        btn_frame = ctk.CTkFrame(header_row, fg_color="transparent")
        btn_frame.grid(row=0, column=1, sticky="e")
        ctk.CTkButton(
            btn_frame, text="+ Add Product", width=140,
            fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"],
            command=self._open_add_dialog,
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            btn_frame, text="Edit", width=80,
            command=self._open_edit_dialog,
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            btn_frame, text="Delete", width=80,
            fg_color=COLORS["danger"], hover_color="#B91C1C",
            command=self._delete_product,
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            btn_frame, text="Adjust Stock", width=110,
            fg_color=COLORS["warning"], hover_color="#B45309",
            command=self._open_stock_dialog,
        ).pack(side="left", padx=4)

        search_row = ctk.CTkFrame(self, fg_color="transparent")
        search_row.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 8))
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._load_products())
        ctk.CTkEntry(
            search_row, placeholder_text="Search products...", width=300,
            textvariable=self.search_var,
        ).pack(side="left")

        cols = ("id", "name", "cost", "price", "stock", "unit", "min_stock")
        headings = {
            "id": "ID",
            "name": "Product Name",
            "cost": "Purchase Price / Unit",
            "price": "Selling Price / Unit",
            "stock": "Stock",
            "unit": "Unit",
            "min_stock": "Low Stock Alert",
        }
        widths = {
            "id": 50, "name": 210, "cost": 150, "price": 150,
            "stock": 90, "unit": 90, "min_stock": 110,
        }
        self.tree, tree_container = styled_treeview(self, cols, headings, widths)
        tree_container.grid(row=2, column=0, sticky="nsew", padx=24, pady=(0, 24))

        self._load_products()

    def _load_products(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        search = self.search_var.get() if hasattr(self, "search_var") else ""
        for p in db.get_products(search):
            stock = p["stock_quantity"]
            tags = ()
            if stock <= p["min_stock_level"]:
                tags = ("low_stock",)
            self.tree.insert(
                "", "end",
                values=(
                    p["id"], p["name"],
                    format_currency(p["cost_price"]),
                    format_currency(p["selling_price"]),
                    f"{stock:g}", p.get("unit") or "kg",
                    f"{p['min_stock_level']:g}",
                ),
                tags=tags,
            )
        self.tree.tag_configure("low_stock", foreground=COLORS["warning"])

    def _get_selected_id(self):
        sel = self.tree.selection()
        if not sel:
            return None
        return str(self.tree.item(sel[0])["values"][0])

    def _open_product_dialog(self, product=None):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Edit Product" if product else "Add Product")
        dialog.geometry("560x680")
        dialog.minsize(500, 560)
        dialog.resizable(True, True)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        form = ctk.CTkScrollableFrame(
            dialog, fg_color=COLORS["card"], corner_radius=12
        )
        form.pack(fill="both", expand=True, padx=18, pady=18)
        form.grid_columnconfigure(0, weight=1)

        fields = {}
        labels = [
            ("name", "Product Name *", "Example: Tomato"),
            ("cost_price", "Purchased Price per Unit *", "Example: 25.00"),
            ("selling_price", "Selling Price per Unit *", "Example: 35.00"),
            ("stock_quantity", "How Many Units / Current Stock *", "Example: 50"),
            ("unit", "Unit *", ""),
            ("min_stock_level", "Low Stock Alert Quantity", "Example: 5"),
            ("description", "Description", "Optional product notes"),
        ]

        ctk.CTkLabel(
            form,
            text="Product Details",
            font=FONT_HEADING,
            text_color=COLORS["text"],
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(18, 4))
        ctk.CTkLabel(
            form,
            text="Enter the product price, available stock and selling unit.",
            font=FONT_SMALL,
            text_color=COLORS["text_muted"],
        ).grid(row=1, column=0, sticky="w", padx=20, pady=(0, 12))

        for i, (key, label, placeholder) in enumerate(labels):
            label_row = 2 + (i * 2)
            input_row = label_row + 1
            ctk.CTkLabel(
                form,
                text=label,
                font=FONT_BODY,
                text_color=COLORS["text"],
                anchor="w",
            ).grid(
                row=label_row, column=0, sticky="ew", padx=20, pady=(9, 3)
            )
            if key == "unit":
                widget = ctk.CTkComboBox(
                    form,
                    values=[
                        "kg", "gram", "piece", "bunch", "dozen",
                        "crate", "box", "bag", "litre",
                    ],
                )
                widget.set(product.get("unit", "kg") if product else "kg")
            elif key == "description":
                widget = ctk.CTkTextbox(form, height=80)
                if product:
                    widget.insert("1.0", product.get("description", ""))
            else:
                widget = ctk.CTkEntry(form, placeholder_text=placeholder)
                if product and product.get(key) is not None:
                    widget.insert(0, str(product[key]))
            widget.grid(
                row=input_row, column=0, sticky="ew", padx=20, pady=(0, 3)
            )
            fields[key] = widget

        error_label = ctk.CTkLabel(
            form, text="", font=FONT_SMALL, text_color=COLORS["danger"], wraplength=470
        )
        error_label.grid(
            row=2 + (len(labels) * 2), column=0, sticky="w", padx=20, pady=(8, 0)
        )

        def save():
            name = fields["name"].get().strip()
            if not name:
                error_label.configure(text="Product Name is required.")
                return
            try:
                purchase_price = float(fields["cost_price"].get())
                selling_price = float(fields["selling_price"].get())
                stock = float(fields["stock_quantity"].get())
                min_stock = float(fields["min_stock_level"].get() or 0)
                if min(purchase_price, selling_price, stock, min_stock) < 0:
                    raise ValueError
            except ValueError:
                error_label.configure(
                    text="Prices and stock quantities must be valid positive numbers."
                )
                return
            data = {
                "name": name,
                "category_id": product.get("category_id") if product else None,
                "unit": fields["unit"].get().strip() or "kg",
                "cost_price": purchase_price,
                "selling_price": selling_price,
                "stock_quantity": stock,
                "min_stock_level": min_stock,
                "description": fields["description"].get("1.0", "end").strip()
                if isinstance(fields["description"], ctk.CTkTextbox) else "",
            }
            try:
                if product:
                    db.update_product(product["id"], data)
                else:
                    db.add_product(data)
                dialog.destroy()
                self._load_products()
            except Exception as e:
                error_label.configure(text=str(e))

        ctk.CTkButton(
            form,
            text="Update Product" if product else "Add Product",
            height=42,
            fg_color=COLORS["primary"],
            command=save,
        ).grid(
            row=3 + (len(labels) * 2), column=0, sticky="ew",
            padx=20, pady=(8, 20)
        )

    def _open_add_dialog(self):
        self._open_product_dialog()

    def _open_edit_dialog(self):
        pid = self._get_selected_id()
        if not pid:
            return
        product = db.get_product(pid)
        if product:
            self._open_product_dialog(product)

    def _delete_product(self):
        pid = self._get_selected_id()
        if not pid:
            return
        if confirm_dialog(self, "Delete Product", "Are you sure you want to delete this product?"):
            db.delete_product(pid)
            self._load_products()

    def _open_stock_dialog(self):
        pid = self._get_selected_id()
        if not pid:
            return
        product = db.get_product(pid)
        if not product:
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title("Adjust Stock")
        dialog.geometry("360x200")
        dialog.resizable(False, False)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text=f"{product['name']}\nCurrent stock: {product['stock_quantity']}",
            font=FONT_BODY,
        ).pack(pady=(20, 12))
        qty_entry = ctk.CTkEntry(dialog, placeholder_text="Quantity (+/-)", width=200)
        qty_entry.pack(pady=8)

        def apply():
            try:
                change = float(qty_entry.get())
                db.adjust_stock(pid, change)
                dialog.destroy()
                self._load_products()
            except ValueError:
                pass

        ctk.CTkButton(
            dialog, text="Apply", width=100, fg_color=COLORS["primary"], command=apply
        ).pack(pady=12)
