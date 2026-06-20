import customtkinter as ctk

from database import db
from .components import confirm_dialog, page_header, styled_treeview
from .theme import COLORS, FONT_BODY, FONT_SMALL


class SuppliersFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color=COLORS["bg"])
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self._build()

    def refresh(self):
        self._load()

    def _build(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(24, 10))
        header.grid_columnconfigure(0, weight=1)
        page_header(header, "Supplier Management", "Manage supplier contact and GST details").grid(
            row=0, column=0, sticky="w"
        )
        buttons = ctk.CTkFrame(header, fg_color="transparent")
        buttons.grid(row=0, column=1)
        ctk.CTkButton(buttons, text="+ Add Supplier", command=self._add).pack(side="left", padx=4)
        ctk.CTkButton(buttons, text="Update", command=self._edit).pack(side="left", padx=4)
        ctk.CTkButton(
            buttons, text="Delete", fg_color=COLORS["danger"], command=self._delete
        ).pack(side="left", padx=4)

        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._load())
        ctk.CTkEntry(
            self, textvariable=self.search_var, width=320,
            placeholder_text="Search suppliers...",
        ).grid(row=1, column=0, sticky="w", padx=24, pady=(0, 8))

        columns = ("id", "name", "phone", "email", "address", "gst")
        headings = {
            "id": "ID", "name": "Supplier Name", "phone": "Contact Number",
            "email": "Email", "address": "Address", "gst": "GST Number",
        }
        widths = {"id": 60, "name": 170, "phone": 120, "email": 180, "address": 240, "gst": 140}
        self.tree, container = styled_treeview(self, columns, headings, widths)
        container.grid(row=2, column=0, sticky="nsew", padx=24, pady=(0, 24))
        self._load()

    def _load(self):
        if not hasattr(self, "tree"):
            return
        self.tree.delete(*self.tree.get_children())
        for supplier in db.get_suppliers(self.search_var.get()):
            self.tree.insert("", "end", values=(
                supplier["id"], supplier["name"], supplier.get("phone") or "—",
                supplier.get("email") or "—", supplier.get("address") or "—",
                supplier.get("gst") or "—",
            ))

    def _selected(self):
        selection = self.tree.selection()
        return str(self.tree.item(selection[0])["values"][0]) if selection else None

    def _form(self, supplier=None):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Update Supplier" if supplier else "Add Supplier")
        dialog.geometry("500x580")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        form = ctk.CTkScrollableFrame(dialog, fg_color=COLORS["card"])
        form.pack(fill="both", expand=True, padx=18, pady=18)
        form.grid_columnconfigure(0, weight=1)
        fields = {}
        definitions = [
            ("name", "Supplier Name *"), ("phone", "Contact Number"),
            ("email", "Email"), ("address", "Address"), ("gst", "GST Number"),
        ]
        for index, (key, label) in enumerate(definitions):
            ctk.CTkLabel(form, text=label, font=FONT_BODY).grid(
                row=index * 2, column=0, sticky="w", padx=18, pady=(10, 3)
            )
            if key == "address":
                widget = ctk.CTkTextbox(form, height=90)
                if supplier:
                    widget.insert("1.0", supplier.get(key, ""))
            else:
                widget = ctk.CTkEntry(form)
                if supplier:
                    widget.insert(0, supplier.get(key, ""))
            widget.grid(row=index * 2 + 1, column=0, sticky="ew", padx=18)
            fields[key] = widget
        error = ctk.CTkLabel(form, text="", font=FONT_SMALL, text_color=COLORS["danger"])
        error.grid(row=10, column=0, sticky="w", padx=18, pady=6)

        def save():
            name = fields["name"].get().strip()
            if not name:
                error.configure(text="Supplier Name is required.")
                return
            data = {
                "name": name, "phone": fields["phone"].get(),
                "email": fields["email"].get(),
                "address": fields["address"].get("1.0", "end").strip(),
                "gst": fields["gst"].get(),
            }
            if supplier:
                db.update_supplier(supplier["id"], data)
            else:
                db.add_supplier(data)
            dialog.destroy()
            self._load()

        ctk.CTkButton(
            form, text="Save Supplier", height=42, command=save
        ).grid(row=11, column=0, sticky="ew", padx=18, pady=(6, 18))

    def _add(self):
        self._form()

    def _edit(self):
        supplier_id = self._selected()
        if supplier_id:
            self._form(db.get_supplier(supplier_id))

    def _delete(self):
        supplier_id = self._selected()
        if supplier_id and confirm_dialog(self, "Delete Supplier", "Delete the selected supplier?"):
            db.delete_supplier(supplier_id)
            self._load()
