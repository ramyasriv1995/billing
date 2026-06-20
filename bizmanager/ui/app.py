import customtkinter as ctk

from .billing import BillingFrame, InvoiceDetailsFrame
from .customers import CustomersFrame
from .inventory import InventoryFrame
from .reports import ReportsFrame
from .settings import SettingsFrame
from .suppliers import SuppliersFrame
from .theme import COLORS, FONT_BODY, FONT_SMALL

NAV_ITEMS = [
  ("billing", "Billing", "🧾"),
  ("inventory", "Inventory", "📦"),
  ("customers", "Customers", "👥"),
  ("suppliers", "Suppliers", "🚚"),
  ("invoice", "Invoice Details", "📄"),
  ("reports", "Reports", "📈"),
  ("settings", "Settings", "⚙️"),
]


class BizManagerApp(ctk.CTk):
  def __init__(self, user: dict, on_logout=None):
    super().__init__()
    self.user = user
    self.on_logout = on_logout
    self.title("Smart Billing and Inventory App")
    self.geometry("1200x750")
    self.minsize(1000, 650)

    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    self.grid_columnconfigure(1, weight=1)
    self.grid_rowconfigure(0, weight=1)

    self._frames = {}
    self._nav_buttons = {}
    self._current = None

    self._build_sidebar()
    self._build_content()
    self.show_frame("billing")

  def _build_sidebar(self):
    sidebar = ctk.CTkFrame(self, width=220, fg_color=COLORS["sidebar"], corner_radius=0)
    sidebar.grid(row=0, column=0, sticky="nsew")
    sidebar.grid_propagate(False)

    ctk.CTkLabel(
      sidebar,
      text="Smart Billing and Inventory App",
      font=("Helvetica", 18, "bold"),
      text_color="white",
    ).pack(anchor="w", padx=20, pady=(24, 4))
    ctk.CTkLabel(
      sidebar, text="Billing • Inventory • Customers",
      font=FONT_BODY, text_color="#94A3B8",
    ).pack(anchor="w", padx=20, pady=(0, 16))

    user_frame = ctk.CTkFrame(sidebar, fg_color=COLORS["sidebar_hover"], corner_radius=8)
    user_frame.pack(fill="x", padx=16, pady=(0, 16))
    display_name = self.user.get("full_name") or self.user["username"]
    ctk.CTkLabel(
      user_frame, text=f"👤 {display_name}", font=FONT_BODY, text_color="white", anchor="w"
    ).pack(fill="x", padx=12, pady=(10, 2))
    ctk.CTkLabel(
      user_frame, text=self.user["username"], font=FONT_SMALL, text_color="#94A3B8", anchor="w"
    ).pack(fill="x", padx=12, pady=(0, 10))

    nav_container = ctk.CTkFrame(sidebar, fg_color="transparent")
    nav_container.pack(fill="both", expand=True, padx=12)

    for key, label, icon in NAV_ITEMS:
      btn = ctk.CTkButton(
        nav_container,
        text=f"  {icon}  {label}",
        anchor="w",
        height=44,
        font=FONT_BODY,
        fg_color="transparent",
        hover_color=COLORS["sidebar_hover"],
        text_color="white",
        command=lambda k=key: self.show_frame(k),
      )
      btn.pack(fill="x", pady=3)
      self._nav_buttons[key] = btn

    ctk.CTkButton(
      sidebar,
      text="  Logout",
      anchor="w",
      height=40,
      font=FONT_BODY,
      fg_color="transparent",
      hover_color=COLORS["danger"],
      text_color="#FCA5A5",
      command=self._logout,
    ).pack(fill="x", padx=12, pady=(8, 16))

  def _build_content(self):
    self.content = ctk.CTkFrame(self, fg_color=COLORS["bg"], corner_radius=0)
    self.content.grid(row=0, column=1, sticky="nsew")
    self.content.grid_columnconfigure(0, weight=1)
    self.content.grid_rowconfigure(0, weight=1)

    self._frames["inventory"] = InventoryFrame(self.content)
    self._frames["customers"] = CustomersFrame(self.content)
    self._frames["suppliers"] = SuppliersFrame(self.content)
    self._frames["billing"] = BillingFrame(self.content)
    self._frames["invoice"] = InvoiceDetailsFrame(self.content)
    self._frames["reports"] = ReportsFrame(self.content)
    self._frames["settings"] = SettingsFrame(self.content)

    for frame in self._frames.values():
      frame.grid(row=0, column=0, sticky="nsew")

  def show_frame(self, name: str):
    if self._current == name:
      if hasattr(self._frames[name], "refresh"):
        self._frames[name].refresh()
      return

    for key, btn in self._nav_buttons.items():
      if key == name:
        btn.configure(fg_color=COLORS["sidebar_active"])
      else:
        btn.configure(fg_color="transparent")

    self._frames[name].tkraise()
    if hasattr(self._frames[name], "refresh"):
      self._frames[name].refresh()
    self._current = name

  def _on_sale_complete(self, sale_id: int):
    self.show_frame("invoice")
    if hasattr(self._frames["invoice"], "refresh"):
      self._frames["invoice"].refresh(highlight_sale_id=sale_id)

  def _logout(self):
    self.destroy()
    if self.on_logout:
      self.on_logout()
