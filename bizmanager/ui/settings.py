from tkinter import filedialog, messagebox

import customtkinter as ctk

from database import db
from .components import page_header
from .theme import COLORS, FONT_BODY, FONT_HEADING, FONT_SMALL


class SettingsFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color=COLORS["bg"])
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build()

    def refresh(self):
        return

    def _build(self):
        page_header(self, "Settings", "Company profile, invoice and backup settings").grid(
            row=0, column=0, sticky="ew", padx=24, pady=(24, 12)
        )
        scroll = ctk.CTkScrollableFrame(self, fg_color=COLORS["card"], corner_radius=12)
        scroll.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 24))
        scroll.grid_columnconfigure(0, weight=1)
        settings = db.get_settings()
        self.fields = {}

        self._section(scroll, 0, "Company Profile")
        definitions = [
            ("company_name", "Company Name"), ("gst", "GST Number"),
            ("address", "Address"), ("phone", "Phone Number"), ("email", "Email"),
        ]
        row = 1
        for key, label in definitions:
            ctk.CTkLabel(scroll, text=label, font=FONT_BODY).grid(
                row=row, column=0, sticky="w", padx=24, pady=(8, 3)
            )
            widget = ctk.CTkTextbox(scroll, height=70) if key == "address" else ctk.CTkEntry(scroll)
            if key == "address":
                widget.insert("1.0", settings.get(key, ""))
            else:
                widget.insert(0, str(settings.get(key, "")))
            widget.grid(row=row + 1, column=0, sticky="ew", padx=24)
            self.fields[key] = widget
            row += 2

        self.logo_var = ctk.StringVar(value=settings.get("logo_path", ""))
        ctk.CTkLabel(scroll, text="Logo", font=FONT_BODY).grid(
            row=row, column=0, sticky="w", padx=24, pady=(8, 3)
        )
        logo_row = ctk.CTkFrame(scroll, fg_color="transparent")
        logo_row.grid(row=row + 1, column=0, sticky="ew", padx=24)
        logo_row.grid_columnconfigure(0, weight=1)
        ctk.CTkEntry(logo_row, textvariable=self.logo_var).grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(logo_row, text="Upload Logo", command=self._logo).grid(row=0, column=1, padx=(8, 0))
        row += 2

        self._section(scroll, row, "Invoice Settings")
        row += 1
        for key, label in [
            ("invoice_prefix", "Invoice Prefix"), ("default_tax", "Tax Settings (%)"),
            ("currency_symbol", "Currency Symbol"),
        ]:
            ctk.CTkLabel(scroll, text=label, font=FONT_BODY).grid(
                row=row, column=0, sticky="w", padx=24, pady=(8, 3)
            )
            widget = ctk.CTkEntry(scroll)
            widget.insert(0, str(settings.get(key, "")))
            widget.grid(row=row + 1, column=0, sticky="ew", padx=24)
            self.fields[key] = widget
            row += 2

        ctk.CTkButton(
            scroll, text="Save Settings", height=42, fg_color=COLORS["success"],
            command=self._save,
        ).grid(row=row, column=0, sticky="ew", padx=24, pady=18)
        row += 1
        self._section(scroll, row, "Backup Settings")
        row += 1
        backup = ctk.CTkFrame(scroll, fg_color="transparent")
        backup.grid(row=row, column=0, sticky="w", padx=24, pady=(8, 24))
        ctk.CTkButton(backup, text="Export Database", command=self._export).pack(side="left", padx=(0, 8))
        ctk.CTkButton(backup, text="Import Database", command=self._import).pack(side="left")

    def _section(self, parent, row, title):
        ctk.CTkLabel(
            parent, text=title, font=FONT_HEADING, text_color=COLORS["primary"]
        ).grid(row=row, column=0, sticky="w", padx=24, pady=(20, 4))

    def _logo(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg *.webp")])
        if path:
            self.logo_var.set(path)

    def _save(self):
        values = {}
        for key, widget in self.fields.items():
            values[key] = (
                widget.get("1.0", "end").strip()
                if isinstance(widget, ctk.CTkTextbox) else widget.get().strip()
            )
        try:
            values["default_tax"] = float(values["default_tax"] or 0)
        except ValueError:
            messagebox.showerror("Invalid tax", "Tax Settings must be numeric.")
            return
        values["logo_path"] = self.logo_var.get()
        db.save_settings(values)
        messagebox.showinfo("Saved", "Settings saved successfully.")

    def _export(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".json", filetypes=[("JSON Backup", "*.json")],
            initialfile="bizmanager_backup.json",
        )
        if path:
            db.export_database(path)
            messagebox.showinfo("Backup complete", f"Database exported to:\n{path}")

    def _import(self):
        path = filedialog.askopenfilename(filetypes=[("JSON Backup", "*.json")])
        if path:
            db.import_database(path)
            messagebox.showinfo("Import complete", "Database imported successfully.")
