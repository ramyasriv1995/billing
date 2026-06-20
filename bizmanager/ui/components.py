import customtkinter as ctk
from tkinter import ttk

from .theme import COLORS, FONT_BODY, FONT_HEADING, FONT_SMALL, FONT_TITLE


def stat_card(parent, title: str, value: str, subtitle: str = "", color: str = None):
    frame = ctk.CTkFrame(parent, fg_color=COLORS["card"], corner_radius=12)
    frame.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(frame, text=title, font=FONT_SMALL, text_color=COLORS["text_muted"]).grid(
        row=0, column=0, sticky="w", padx=20, pady=(16, 4)
    )
    ctk.CTkLabel(
        frame,
        text=value,
        font=("Helvetica", 28, "bold"),
        text_color=color or COLORS["text"],
    ).grid(row=1, column=0, sticky="w", padx=20, pady=(0, 4))
    if subtitle:
        ctk.CTkLabel(frame, text=subtitle, font=FONT_SMALL, text_color=COLORS["text_muted"]).grid(
            row=2, column=0, sticky="w", padx=20, pady=(0, 16)
        )
    else:
        ctk.CTkLabel(frame, text="").grid(row=2, column=0, pady=(0, 8))
    return frame


def page_header(parent, title: str, subtitle: str = ""):
    header = ctk.CTkFrame(parent, fg_color="transparent")
    header.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(header, text=title, font=FONT_TITLE, text_color=COLORS["text"]).grid(
        row=0, column=0, sticky="w"
    )
    if subtitle:
        ctk.CTkLabel(
            header, text=subtitle, font=FONT_BODY, text_color=COLORS["text_muted"]
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))
    return header


def styled_treeview(parent, columns: list, headings: dict, widths: dict):
    style = ttk.Style()
    style.theme_use("clam")
    style.configure(
        "Biz.Treeview",
        background=COLORS["card"],
        foreground=COLORS["text"],
        fieldbackground=COLORS["card"],
        rowheight=32,
        font=FONT_BODY,
        borderwidth=0,
    )
    style.configure(
        "Biz.Treeview.Heading",
        background=COLORS["bg"],
        foreground=COLORS["text"],
        font=FONT_HEADING,
        relief="flat",
    )
    style.map("Biz.Treeview", background=[("selected", COLORS["primary"])])

    container = ctk.CTkFrame(parent, fg_color=COLORS["card"], corner_radius=12)
    container.grid_columnconfigure(0, weight=1)
    container.grid_rowconfigure(0, weight=1)

    tree = ttk.Treeview(
        container,
        columns=columns,
        show="headings",
        style="Biz.Treeview",
        selectmode="browse",
    )
    for col in columns:
        tree.heading(col, text=headings.get(col, col))
        tree.column(col, width=widths.get(col, 120), anchor="w")

    scroll_y = ctk.CTkScrollbar(container, command=tree.yview)
    tree.configure(yscrollcommand=scroll_y.set)
    tree.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
    scroll_y.grid(row=0, column=1, sticky="ns", pady=12)

    return tree, container


def confirm_dialog(parent, title: str, message: str) -> bool:
    result = {"value": False}

    dialog = ctk.CTkToplevel(parent)
    dialog.title(title)
    dialog.geometry("400x180")
    dialog.resizable(False, False)
    dialog.transient(parent)
    dialog.grab_set()

    ctk.CTkLabel(dialog, text=message, font=FONT_BODY, wraplength=360).pack(
        padx=24, pady=(28, 20)
    )

    btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    btn_frame.pack(pady=8)

    def on_yes():
        result["value"] = True
        dialog.destroy()

    ctk.CTkButton(btn_frame, text="Cancel", width=100, fg_color=COLORS["text_muted"], command=dialog.destroy).pack(
        side="left", padx=8
    )
    ctk.CTkButton(
        btn_frame, text="Confirm", width=100, fg_color=COLORS["danger"], command=on_yes
    ).pack(side="left", padx=8)

    dialog.wait_window()
    return result["value"]


def format_currency(amount: float) -> str:
    return f"₹{amount:,.2f}"
