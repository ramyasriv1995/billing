import customtkinter as ctk

from database import db
from .theme import COLORS, FONT_BODY, FONT_HEADING, FONT_TITLE


class LoginWindow(ctk.CTk):
  def __init__(self, on_login_success):
    super().__init__()
    self.on_login_success = on_login_success
    self.title("Smart Billing and Inventory App")
    self.geometry("420x480")
    self.resizable(False, False)

    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    self._center_window()
    self._build()

  def _center_window(self):
    self.update_idletasks()
    w, h = 420, 480
    x = (self.winfo_screenwidth() // 2) - (w // 2)
    y = (self.winfo_screenheight() // 2) - (h // 2)
    self.geometry(f"{w}x{h}+{x}+{y}")

  def _build(self):
    container = ctk.CTkFrame(self, fg_color=COLORS["card"], corner_radius=16)
    container.pack(fill="both", expand=True, padx=32, pady=32)

    ctk.CTkLabel(
      container,
      text="Smart Billing and Inventory App",
      font=FONT_TITLE,
      text_color=COLORS["primary"],
    ).pack(pady=(28, 4))
    ctk.CTkLabel(
      container,
      text="Billing • Inventory • Sales",
      font=FONT_BODY,
      text_color=COLORS["text_muted"],
    ).pack(pady=(0, 28))

    ctk.CTkLabel(container, text="Username", font=FONT_BODY, anchor="w").pack(
      fill="x", padx=28, pady=(0, 4)
    )
    self.username_entry = ctk.CTkEntry(container, placeholder_text="Enter username", height=40)
    self.username_entry.pack(fill="x", padx=28, pady=(0, 12))
    self.username_entry.insert(0, "admin")

    ctk.CTkLabel(container, text="Password", font=FONT_BODY, anchor="w").pack(
      fill="x", padx=28, pady=(0, 4)
    )
    self.password_entry = ctk.CTkEntry(
      container, placeholder_text="Enter password", show="•", height=40
    )
    self.password_entry.pack(fill="x", padx=28, pady=(0, 8))
    self.password_entry.bind("<Return>", lambda e: self._login())

    self.error_label = ctk.CTkLabel(
      container, text="", font=FONT_BODY, text_color=COLORS["danger"]
    )
    self.error_label.pack(pady=(0, 8))

    ctk.CTkButton(
      container,
      text="Sign In",
      height=44,
      font=FONT_HEADING,
      fg_color=COLORS["primary"],
      hover_color=COLORS["primary_hover"],
      command=self._login,
    ).pack(fill="x", padx=28, pady=(8, 16))

    ctk.CTkLabel(
      container,
      text="Default: admin / admin123",
      font=("Helvetica", 11),
      text_color=COLORS["text_muted"],
    ).pack(pady=(0, 20))

    self.username_entry.focus()

  def _login(self):
    username = self.username_entry.get().strip()
    password = self.password_entry.get()

    if not username or not password:
      self.error_label.configure(text="Please enter username and password.")
      return

    user = db.authenticate_user(username, password)
    if not user:
      self.error_label.configure(text="Invalid username or password.")
      self.password_entry.delete(0, "end")
      return

    self.on_login_success(user)
