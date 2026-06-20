import customtkinter as ctk

from database import db
from .components import confirm_dialog, page_header, styled_treeview
from .theme import COLORS, FONT_BODY, FONT_HEADING, FONT_SMALL


class CustomersFrame(ctk.CTkFrame):
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

        page_header(
            header_row, "Customers", "Manage customer contact, address, and GST details"
        ).grid(row=0, column=0, sticky="w")

        btn_frame = ctk.CTkFrame(header_row, fg_color="transparent")
        btn_frame.grid(row=0, column=1, sticky="e")
        ctk.CTkButton(
            btn_frame, text="+ Add Customer", width=140,
            fg_color=COLORS["primary"], command=self._open_add_dialog,
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            btn_frame, text="Edit", width=80,
            command=self._open_edit_dialog,
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            btn_frame, text="Delete", width=80,
            fg_color=COLORS["danger"], hover_color="#B91C1C",
            command=self._delete_customer,
        ).pack(side="left", padx=4)

        search_row = ctk.CTkFrame(self, fg_color="transparent")
        search_row.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 8))
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._load_customers())
        ctk.CTkEntry(
            search_row, placeholder_text="Search name, phone, email, address, or GST...",
            width=300, textvariable=self.search_var,
        ).pack(side="left")

        cols = ("id", "name", "phone", "email", "address", "gst")
        headings = {
            "id": "ID", "name": "Customer Name", "phone": "Phone",
            "email": "Email", "address": "Address", "gst": "GST",
        }
        widths = {"id": 60, "name": 150, "phone": 110, "email": 170, "address": 220, "gst": 130}
        self.tree, tree_container = styled_treeview(self, cols, headings, widths)
        tree_container.grid(row=2, column=0, sticky="nsew", padx=24, pady=(0, 24))

        self._load_customers()

    def _load_customers(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        search = self.search_var.get() if hasattr(self, "search_var") else ""
        for c in db.get_customers(search):
            self.tree.insert(
                "", "end",
                values=(
                    c["id"], c["name"], c.get("phone") or "—", c.get("email") or "—",
                    c.get("address") or "—",
                    c.get("gst") or "—",
                ),
            )

    def _get_selected_id(self):
        sel = self.tree.selection()
        if not sel:
            return None
        return str(self.tree.item(sel[0])["values"][0])

    def _open_customer_dialog(self, customer=None):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Edit Customer" if customer else "Add Customer")
        dialog.geometry("560x650")
        dialog.minsize(500, 540)
        dialog.resizable(True, True)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        form = ctk.CTkScrollableFrame(
            dialog, fg_color=COLORS["card"], corner_radius=12
        )
        form.pack(fill="both", expand=True, padx=18, pady=18)
        form.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            form,
            text="Customer Details",
            font=FONT_HEADING,
            text_color=COLORS["text"],
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(18, 4))
        ctk.CTkLabel(
            form,
            text="Add contact and billing information for this customer.",
            font=FONT_SMALL,
            text_color=COLORS["text_muted"],
        ).grid(row=1, column=0, sticky="w", padx=20, pady=(0, 12))

        fields = {}
        for i, (key, label, placeholder) in enumerate([
            ("name", "Customer Name *", "Enter customer name"),
            ("address", "Address", "Enter complete billing address"),
            ("gst", "GST Number", "Example: 29ABCDE1234F1Z5"),
            ("phone", "Phone Number", "Enter phone number"),
            ("email", "Email ID", "Enter email address"),
        ]):
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
            if key == "address":
                widget = ctk.CTkTextbox(form, height=90)
                if customer:
                    widget.insert("1.0", customer.get("address", ""))
            else:
                widget = ctk.CTkEntry(form, placeholder_text=placeholder)
                if customer and customer.get(key):
                    widget.insert(0, str(customer[key]))
            widget.grid(
                row=input_row, column=0, sticky="ew", padx=20, pady=(0, 3)
            )
            fields[key] = widget

        error_label = ctk.CTkLabel(
            form, text="", font=FONT_SMALL, text_color=COLORS["danger"]
        )
        error_label.grid(row=12, column=0, sticky="w", padx=20, pady=(8, 0))

        def save():
            name = fields["name"].get().strip()
            if not name:
                error_label.configure(text="Customer Name is required.")
                return
            data = {
                "name": name,
                "phone": fields["phone"].get().strip(),
                "email": fields["email"].get().strip(),
                "address": fields["address"].get("1.0", "end").strip()
                if hasattr(fields["address"], "get")
                else "",
                "gst": fields["gst"].get().strip(),
            }
            if customer:
                db.update_customer(customer["id"], data)
            else:
                db.add_customer(data)
            dialog.destroy()
            self._load_customers()

        ctk.CTkButton(
            form,
            text="Update Customer" if customer else "Add Customer",
            height=42,
            fg_color=COLORS["primary"],
            command=save,
        ).grid(row=13, column=0, sticky="ew", padx=20, pady=(8, 20))

    def _open_add_dialog(self):
        self._open_customer_dialog()

    def _open_edit_dialog(self):
        customer_id = self._get_selected_id()
        if not customer_id:
            return
        customer = db.get_customer(customer_id)
        if customer:
            self._open_customer_dialog(customer)

    def _delete_customer(self):
        customer_id = self._get_selected_id()
        if not customer_id:
            return
        if confirm_dialog(self, "Delete Customer", "Are you sure you want to delete this customer?"):
            db.delete_customer(customer_id)
            self._load_customers()
