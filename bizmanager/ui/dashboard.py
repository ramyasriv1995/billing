import customtkinter as ctk

from database import db
from .components import format_currency, page_header, stat_card
from .theme import COLORS, FONT_BODY, FONT_HEADING, FONT_SMALL


class DashboardFrame(ctk.CTkFrame):
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
        stats = db.get_dashboard_stats()

        page_header(self, "Dashboard", "Overview of your business").grid(
            row=0, column=0, sticky="ew", padx=24, pady=(24, 16)
        )

        cards = ctk.CTkFrame(self, fg_color="transparent")
        cards.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 16))
        for i in range(4):
            cards.grid_columnconfigure(i, weight=1)

        stat_card(
            cards, "Today's Revenue", format_currency(stats["today_revenue"]),
            f"{stats['today_sales_count']} sale(s) today", COLORS["success"]
        ).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        stat_card(
            cards, "Total Revenue", format_currency(stats["total_revenue"]),
            f"{stats['total_sales_count']} total sales", COLORS["primary"]
        ).grid(row=0, column=1, sticky="ew", padx=8)
        stat_card(
            cards, "Products", str(stats["total_products"]),
            f"Stock value: {format_currency(stats['total_stock_value'])}"
        ).grid(row=0, column=2, sticky="ew", padx=8)
        stat_card(
            cards, "Low Stock Alerts", str(stats["low_stock_count"]),
            "Items need restocking", COLORS["warning"] if stats["low_stock_count"] else COLORS["text"]
        ).grid(row=0, column=3, sticky="ew", padx=(8, 0))

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=2, column=0, sticky="nsew", padx=24, pady=(0, 24))
        bottom.grid_columnconfigure(0, weight=1)
        bottom.grid_columnconfigure(1, weight=1)
        bottom.grid_rowconfigure(0, weight=1)

        self._recent_sales_panel(bottom, stats["recent_sales"])
        self._low_stock_panel(bottom, stats["low_stock_products"])

    def _recent_sales_panel(self, parent, sales):
        panel = ctk.CTkFrame(parent, fg_color=COLORS["card"], corner_radius=12)
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(panel, text="Recent Sales", font=FONT_HEADING).grid(
            row=0, column=0, sticky="w", padx=20, pady=(16, 8)
        )

        if not sales:
            ctk.CTkLabel(
                panel, text="No sales yet. Create your first sale!", text_color=COLORS["text_muted"]
            ).grid(row=1, column=0, padx=20, pady=20)
            return

        for i, sale in enumerate(sales):
            row = ctk.CTkFrame(panel, fg_color=COLORS["bg"], corner_radius=8)
            row.grid(row=i + 1, column=0, sticky="ew", padx=16, pady=4)
            row.grid_columnconfigure(0, weight=1)

            customer = sale.get("customer_name") or "Walk-in"
            ctk.CTkLabel(
                row, text=f"{sale['invoice_number']} — {customer}", font=FONT_BODY, anchor="w"
            ).grid(row=0, column=0, sticky="ew", padx=12, pady=8)
            ctk.CTkLabel(
                row,
                text=f"{format_currency(sale['total'])}  •  {sale['created_at'][:16]}",
                font=FONT_SMALL,
                text_color=COLORS["text_muted"],
            ).grid(row=0, column=1, padx=12, pady=8)

    def _low_stock_panel(self, parent, products):
        panel = ctk.CTkFrame(parent, fg_color=COLORS["card"], corner_radius=12)
        panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(panel, text="Low Stock Items", font=FONT_HEADING).grid(
            row=0, column=0, sticky="w", padx=20, pady=(16, 8)
        )

        if not products:
            ctk.CTkLabel(
                panel, text="All products are well stocked.", text_color=COLORS["success"]
            ).grid(row=1, column=0, padx=20, pady=20)
            return

        for i, product in enumerate(products):
            row = ctk.CTkFrame(panel, fg_color=COLORS["bg"], corner_radius=8)
            row.grid(row=i + 1, column=0, sticky="ew", padx=16, pady=4)
            row.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(row, text=product["name"], font=FONT_BODY, anchor="w").grid(
                row=0, column=0, sticky="ew", padx=12, pady=8
            )
            ctk.CTkLabel(
                row,
                text=f"Stock: {product['stock_quantity']} / Min: {product['min_stock_level']}",
                font=FONT_SMALL,
                text_color=COLORS["warning"],
            ).grid(row=0, column=1, padx=12, pady=8)
