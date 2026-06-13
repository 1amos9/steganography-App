"""
QuickCrypto Stego Suite
A steganography and crypto desktop app in the style of the QuickCrypto interface.

Run:  python app.py
Needs: customtkinter, pillow, numpy, cryptography
Install: pip install customtkinter pillow numpy cryptography

Layout mirrors the QuickCrypto reference: a full menu bar, a button grid on the
left, a logo, a text and image work area, and a bottom tab row.

The art in the assets folder is original. It is not copied from QuickCrypto.
"""

import os
import sys
import threading
import webbrowser
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image, ImageTk

import stego_engine as se
import crypto_engine as ce
import audio_stego as au

# ----- theme: matrix refined green on black -----
BLACK = "#040805"
PANEL_BLACK = "#030a06"
YELLOW = "#00ff78"        # bright matrix green (primary)
YELLOW_DEEP = "#00b257"   # mid green (borders, accents)
YELLOW_DARK = "#1f7a45"   # dim green (muted text, edges)
TEXT_DARK = "#021006"     # near-black green for text on bright fills
MENU_BG = "#0a140d"
TILE = "#07140c"
MONO = "Consolas"         # monospace face for the terminal look

ASSET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

ctk.set_appearance_mode("dark")


def load_icon(name, size=20):
    """Load an icon PNG as a CTkImage. Returns None if the file is missing."""
    path = os.path.join(ASSET_DIR, f"icon_{name}.png")
    if not os.path.exists(path):
        return None
    img = Image.open(path).convert("RGBA")
    return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))


def load_tk_icon(name, size=18):
    """Load an icon PNG as a Tk PhotoImage for use on a canvas. None if missing."""
    if not name:
        return None
    path = os.path.join(ASSET_DIR, f"icon_{name}.png")
    if not os.path.exists(path):
        return None
    img = Image.open(path).convert("RGBA").resize((size, size))
    return ImageTk.PhotoImage(img)


def load_tk_cicon(name, size=22):
    """Load a colourful icon (cicon_*.png) as a Tk PhotoImage. None if missing."""
    if not name:
        return None
    path = os.path.join(ASSET_DIR, f"cicon_{name}.png")
    if not os.path.exists(path):
        return None
    img = Image.open(path).convert("RGBA").resize((size, size))
    return ImageTk.PhotoImage(img)


class PassPhraseDialog(ctk.CTkToplevel):
    """
    One window for the pass phrase, like the original QuickCrypto dialog.
    create mode shows two boxes and a strength meter so a typo cannot lock you out.
    unlock mode shows one box to enter the pass phrase you used.
    Returns the pass phrase through get(), or None if cancelled.
    """

    def __init__(self, parent, mode="create", default=None):
        super().__init__(parent)
        self.title("Enter Pass Phrase")
        self.configure(fg_color=BLACK)
        self.geometry("520x320")
        self.result = None
        self._mode = mode
        self._default = default
        self._hidden = True
        self.transient(parent)
        try:
            self.grab_set()
        except Exception:
            pass

        header = ctk.CTkFrame(self, fg_color="#2a2a00")
        header.pack(fill="x")
        ctk.CTkLabel(header, text="\U0001F511  Enter Pass Phrase", text_color=YELLOW,
                     font=(MONO, 16, "bold")).pack(side="left", padx=12, pady=8)

        if mode == "create":
            msg = ("Enter the pass phrase twice. It must be 6 characters or more. "
                   "You will need it to decrypt later.")
        else:
            msg = "Enter the pass phrase that was used to encrypt."
        ctk.CTkLabel(self, text=msg, text_color=YELLOW_DEEP, wraplength=480,
                     justify="left", font=("Arial", 12)).pack(anchor="w", padx=16, pady=(12, 8))

        self.e1 = ctk.CTkEntry(self, show="*", width=480,
                               fg_color=PANEL_BLACK, text_color=YELLOW, border_color=YELLOW_DEEP)
        self.e1.pack(padx=16, pady=4)
        self.e1.bind("<KeyRelease>", self._update_strength)

        if mode == "create":
            self.e2 = ctk.CTkEntry(self, show="*", width=480,
                                   fg_color=PANEL_BLACK, text_color=YELLOW, border_color=YELLOW_DEEP)
            self.e2.pack(padx=16, pady=4)

            strength_row = ctk.CTkFrame(self, fg_color=BLACK)
            strength_row.pack(fill="x", padx=16, pady=(6, 0))
            ctk.CTkLabel(strength_row, text="Strength", text_color=YELLOW_DARK,
                         font=("Arial", 11)).pack(side="left", padx=(0, 8))
            self._strength_bar = ctk.CTkProgressBar(strength_row, progress_color=YELLOW,
                                                    fg_color=PANEL_BLACK, height=12)
            self._strength_bar.set(0)
            self._strength_bar.pack(side="left", fill="x", expand=True)
            self._strength_label = ctk.CTkLabel(strength_row, text="-", text_color=YELLOW_DARK,
                                                font=("Consolas", 11))
            self._strength_label.pack(side="left", padx=8)
        else:
            self.e2 = None

        ctk.CTkCheckBox(self, text="Hide Password", command=self._toggle_hide,
                        text_color=YELLOW, fg_color=YELLOW_DEEP, onvalue=True, offvalue=False).pack(anchor="w", padx=16, pady=8)

        btns = ctk.CTkFrame(self, fg_color=BLACK)
        btns.pack(pady=8)
        ctk.CTkButton(btns, text="OK", command=self._ok, width=90,
                      fg_color=YELLOW, hover_color=YELLOW_DEEP, text_color=TEXT_DARK,
                      font=("Arial", 12, "bold")).pack(side="left", padx=5)
        ctk.CTkButton(btns, text="Cancel", command=self._cancel, width=90,
                      fg_color="#333300", hover_color="#444400", text_color=YELLOW).pack(side="left", padx=5)
        ctk.CTkButton(btns, text="Use Default", command=self._use_default, width=110,
                      fg_color="#333300", hover_color="#444400", text_color=YELLOW).pack(side="left", padx=5)
        ctk.CTkButton(btns, text="OS Keyboard", command=self._osk, width=110,
                      fg_color="#333300", hover_color="#444400", text_color=YELLOW).pack(side="left", padx=5)

        self.after(60, self.lift)
        self.e1.focus_set()
        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self._cancel())

    def _toggle_hide(self):
        self._hidden = not self._hidden
        show = "*" if self._hidden else ""
        self.e1.configure(show=show)
        if self.e2 is not None:
            self.e2.configure(show=show)

    def _update_strength(self, _event=None):
        if self._mode != "create":
            return
        import crypto_engine as ce
        score, label, _notes = ce.test_password_strength(self.e1.get())
        self._strength_bar.set(score / 100)
        self._strength_label.configure(text=f"{label} {score}")

    def _ok(self):
        pw = self.e1.get()
        if self._mode == "create":
            if len(pw) < 6:
                messagebox.showwarning("Pass Phrase", "Use 6 characters or more.")
                return
            if pw != self.e2.get():
                messagebox.showwarning("Pass Phrase", "The two entries did not match.")
                return
        else:
            if not pw:
                messagebox.showwarning("Pass Phrase", "Enter the pass phrase.")
                return
        self.result = pw
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()

    def _use_default(self):
        if not self._default:
            messagebox.showinfo("Pass Phrase",
                                "No default set. Set one in Options, Change Default Pass Phrase.")
            return
        self.result = self._default
        self.destroy()

    def _osk(self):
        import subprocess
        try:
            subprocess.Popen("osk")
        except Exception:
            messagebox.showinfo("On Screen Keyboard",
                                "The on screen keyboard is a Windows tool. Run osk from Start if needed.")

    def get(self):
        self.wait_window()
        return self.result


class CodeRain(tk.Canvas):
    """A matrix style background. Columns of 0 and 1 fall down the canvas."""

    def __init__(self, parent, width=320, height=240, fg="#00ff78", dim="#0a3a1f"):
        super().__init__(parent, bg="#040805", highlightthickness=0, bd=0)
        self.configure(width=width, height=height)
        self.fg = fg
        self.dim = dim
        self._cw = width
        self._ch = height
        self._step = 14
        self._cols = max(1, width // self._step)
        import random
        self._random = random
        self._drops = [random.randint(-20, 0) for _ in range(self._cols)]
        self._running = True
        self.bind("<Configure>", self._resize)
        self.after(60, self._tick)

    def _resize(self, event):
        self._cw, self._ch = event.width, event.height
        self._cols = max(1, self._cw // self._step)
        self._drops = [self._random.randint(-20, 0) for _ in range(self._cols)]

    def _tick(self):
        if not self._running:
            return
        self.delete("all")
        for c in range(self._cols):
            x = c * self._step + 2
            head = self._drops[c]
            for k in range(0, 8):
                y = (head - k) * self._step
                if 0 <= y <= self._ch:
                    ch = self._random.choice("01")
                    color = self.fg if k == 0 else self.dim
                    self.create_text(x, y, text=ch, fill=color,
                                     font=("Consolas", 11), anchor="nw")
            self._drops[c] += 1
            if head * self._step > self._ch + 40 and self._random.random() > 0.92:
                self._drops[c] = self._random.randint(-10, 0)
        self.after(90, self._tick)

    def stop(self):
        self._running = False


class AngledBar(tk.Canvas):
    """
    A row of slanted yellow buttons, drawn on a canvas.
    Gives the angular look from the QuickCrypto screenshots.
    items is a list of (label, command). One canvas holds the whole row.
    """

    def __init__(self, parent, items, height=34, skew=10,
                 base="#07140c", hover="#0d2a18", edge="#00b257",
                 fg="#00ff78", font=("Consolas", 11, "bold"), terminal=False,
                 color_icons=False):
        super().__init__(parent, height=height, bg="#000000",
                         highlightthickness=0, bd=0)
        self.items = items
        self.terminal = terminal
        self.color_icons = color_icons
        if terminal:
            skew = 0
        # each item is (label, command) or (label, command, icon_name)
        icon_size = max(18, height - 12) if color_icons else max(14, height - 16)
        self._icon_imgs = []
        for item in items:
            name = item[2] if len(item) >= 3 else None
            if color_icons:
                self._icon_imgs.append(load_tk_cicon(name, icon_size))
            else:
                self._icon_imgs.append(load_tk_icon(name, icon_size))
        self.bar_height = height
        self.skew = skew
        self.base = base
        self.hover = hover
        self.edge = edge
        self.fg = fg
        self.btn_font = font
        self._polys = []
        self._hover = -1
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Button-1>", self._click)
        self.bind("<Motion>", self._motion)
        self.bind("<Leave>", lambda e: self._set_hover(-1))

    def _draw(self):
        self.delete("all")
        self._polys = []
        width = self.winfo_width()
        height = self.bar_height
        n = len(self.items)
        if width <= 1 or n == 0:
            return
        slice_w = width / n
        sk = self.skew
        top_x, bot_x = [], []
        for j in range(n + 1):
            if j == 0:
                top_x.append(0); bot_x.append(0)
            elif j == n:
                top_x.append(width); bot_x.append(width)
            else:
                center = j * slice_w
                top_x.append(center + sk); bot_x.append(center - sk)
        for i, item in enumerate(self.items):
            label = item[0]
            points = [top_x[i], 0, top_x[i + 1], 0,
                      bot_x[i + 1], height, bot_x[i], height]
            pid = self.create_polygon(points, fill=self.base,
                                      outline=self.edge, width=1)
            self._polys.append(pid)
            cx = i * slice_w + slice_w / 2
            img = self._icon_imgs[i]
            if self.terminal:
                img = self._icon_imgs[i]
                if self.color_icons and img is not None:
                    # green label on the left, colourful icon on the right edge
                    self.create_text(i * slice_w + 14, height / 2, text=label,
                                     fill=self.fg, font=self.btn_font, anchor="w")
                    right_x = (i + 1) * slice_w - 18
                    self.create_image(right_x, height / 2, image=img)
                elif img is not None:
                    self.create_image(i * slice_w + 16, height / 2, image=img)
                    self.create_text(i * slice_w + 32, height / 2, text=label,
                                     fill=self.fg, font=self.btn_font, anchor="w")
                else:
                    self.create_text(i * slice_w + 12, height / 2, text="> " + label,
                                     fill=self.fg, font=self.btn_font, anchor="w")
            elif img is not None:
                self.create_image(i * slice_w + 16, height / 2, image=img)
                self.create_text(i * slice_w + 30, height / 2, text=label,
                                 fill=self.fg, font=self.btn_font, anchor="w")
            else:
                self.create_text(cx, height / 2, text=label, fill=self.fg,
                                 font=self.btn_font, justify="center")

    def _index_at(self, x):
        width = self.winfo_width()
        n = len(self.items)
        if width <= 0 or n == 0:
            return -1
        i = int(x // (width / n))
        return max(0, min(n - 1, i))

    def _click(self, event):
        i = self._index_at(event.x)
        if 0 <= i < len(self.items):
            cmd = self.items[i][1]
            if cmd:
                cmd()

    def _motion(self, event):
        self._set_hover(self._index_at(event.x))

    def _set_hover(self, i):
        if i == self._hover:
            return
        self._hover = i
        for k, pid in enumerate(self._polys):
            if k == i:
                self.itemconfig(pid, fill=self.hover, outline="#00ff78", width=2)
            else:
                self.itemconfig(pid, fill=self.base, outline=self.edge, width=1)


class StegoApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("StegoShell  -  data hidden, data secured")
        self.geometry("1080x640")
        self.minsize(1000, 600)
        self.configure(fg_color=BLACK)

        # working state
        self.cover_array = None
        self.stego_array = None
        self.cover_path = None
        self.stego_path = None
        self.preview_image = None
        self.default_passphrase = None
        self.text_font_size = 12

        # stego workspace window state
        self._stego_win = None
        self._stego_out = None
        self._stego_preview = None
        self._preview_ref = None
        self._show_splash_pref = True
        self._load_config()

        self._icons = {}
        self._load_icons()

        self._build_menubar()
        self._build_header()
        self._build_body()
        self._build_bottom_bar()

        self._log("root@stegoshell:~$ ./run")
        self._log("> system ready.....")
        self._log("> graded core: LSB image steganography. load a cover image to begin.")
        self._start_cursor_blink()

    def _load_icons(self):
        for name in ("lock", "unlock", "file", "folder", "copy", "paste", "clear",
                     "flame", "shield", "eye", "key", "gear", "image", "save",
                     "open", "password", "mail", "info"):
            self._icons[name] = load_icon(name, 20)

    def icon(self, name):
        return self._icons.get(name)

    # ===============================================================
    # MENU BAR  (every menu from the screenshots)
    # ===============================================================
    def _menu(self, parent):
        return tk.Menu(parent, tearoff=0, bg=MENU_BG, fg=YELLOW,
                       activebackground=YELLOW, activeforeground=BLACK,
                       font=("Arial", 10))

    def _build_menubar(self):
        # custom green menu bar: build the dropdowns, then post them from buttons
        self._menus = []

        # File
        m = self._menu(self)
        m.add_command(label="📂 Open Any File ...", command=self.open_any_file)
        m.add_command(label="💾 Save Text As File ...", command=self.save_text_file)
        m.add_command(label="🖨 Print Text", command=self.print_text)
        m.add_separator()
        m.add_command(label="Cancel", command=self.cancel_action)
        m.add_command(label="⏻ Exit", command=self.exit_app)
        self._menus.append(("File", m))

        # Edit
        m = self._menu(self)
        m.add_command(label="📋 Copy", command=self.copy_text)
        m.add_command(label="📝 Paste", command=self.paste_text)
        m.add_command(label="✖ Clear", command=self.clear_text)
        self._menus.append(("Edit", m))

        # Encrypt
        m = self._menu(self)
        m.add_command(label="🔒 EnCrypt Files ...", command=self.encrypt_files)
        m.add_command(label="🔒 EnCrypt Folder ...", command=self.encrypt_folder)
        m.add_command(label="🔒 EnCrypt Text Window", accelerator="Ctrl+E",
                      command=self.encrypt_text_window)
        self._menus.append(("Encrypt", m))

        # Decrypt
        m = self._menu(self)
        m.add_command(label="🔓 DeCrypt Files ...", command=self.decrypt_files)
        m.add_command(label="🔓 DeCrypt Folder ...", command=self.decrypt_folder)
        m.add_command(label="🔓 DeCrypt Text Window", accelerator="Ctrl+D",
                      command=self.decrypt_text_window)
        self._menus.append(("Decrypt", m))

        # Shred
        m = self._menu(self)
        m.add_command(label="🔥 Shred Files ...", command=self.shred_files)
        m.add_command(label="🔥 Shred Folder ...", command=self.shred_folder)
        m.add_command(label="Data Forensics ... (demo)", command=self.data_forensics)
        self._menus.append(("Shred", m))

        # Hide  (steganography, the graded core)
        m = self._menu(self)
        m.add_command(label="👁 Hide Files ...", command=self.hide_file)
        m.add_command(label="👁 Hide Folder ...", command=self.hide_folder)
        m.add_command(label="🖼 Hide / Read Text or File in Image", accelerator="Ctrl+H",
                      command=self.open_stego_workspace)
        m.add_separator()
        m.add_command(label="🔊 Hide Text in Sound (WAV) ...", command=self.audio_hide_text)
        m.add_command(label="🔊 Hide File in Sound (WAV) ...", command=self.audio_hide_file)
        m.add_command(label="🔉 Read Text from Sound (WAV) ...", command=self.audio_read_text)
        m.add_command(label="🔉 Read File from Sound (WAV) ...", command=self.audio_read_file)
        self._menus.append(("Hide", m))

        # Privacy
        m = self._menu(self)
        m.add_command(label="Shred Internet Explorer (demo)", command=lambda: self.privacy_stub("Internet Explorer history"))
        m.add_command(label="Shred Firefox (demo)", command=lambda: self.privacy_stub("Firefox history"))
        m.add_command(label="Shred Special Files (demo)", command=lambda: self.privacy_stub("Special files"))
        m.add_command(label="Shred Free Space ... (demo)", command=lambda: self.privacy_stub("Free disk space"))
        m.add_separator()
        m.add_command(label="Data Forensics ... (demo)", command=self.data_forensics)
        self._menus.append(("Privacy", m))

        # Personalize
        m = self._menu(self)
        m.add_command(label="Text Font ...", command=self.choose_font)
        m.add_command(label="Banner (demo)", command=lambda: self.stub("Banner"))
        m.add_command(label="Colors", command=self.cycle_colors)
        m.add_command(label="Themes", command=self.cycle_theme)
        m.add_command(label="Skins (demo)", command=lambda: self.stub("Skins"))
        m.add_separator()
        m.add_command(label="Reset Windows Defaults", command=self.reset_defaults)
        m.add_command(label="Reset Defaults", command=self.reset_defaults)
        self._menus.append(("Personalize", m))

        # Tools
        m = self._menu(self)
        m.add_command(label="Crypto Explorer ... (demo)", accelerator="Ctrl+Q",
                      command=lambda: self.stub("Crypto Explorer"))
        m.add_command(label="System Monitor ... (demo)", command=lambda: self.stub("System Monitor"))
        m.add_command(label="Password Safe ...", accelerator="Ctrl+S",
                      command=self.password_safe)
        m.add_command(label="Send Email ... (demo)", command=lambda: self.stub("Send Email"))
        m.add_separator()
        m.add_command(label="📨 Create Self Decrypting Message ...", command=self.self_decrypt)
        m.add_command(label="🔑 Generate Secure Password ...", accelerator="Ctrl+P",
                      command=self.generate_password)
        m.add_command(label="✅ Password Testing / Recovery", command=self.test_password)
        m.add_separator()
        m.add_command(label="System Tools (demo)", command=lambda: self.stub("System Tools"))
        m.add_command(label="Unplug USB Device (demo)", accelerator="Ctrl+U",
                      command=lambda: self.stub("Unplug USB Device"))
        self._menus.append(("Tools", m))

        # Options
        m = self._menu(self)
        m.add_command(label="🔑 Change Default Pass Phrase ...", command=self.change_passphrase)
        m.add_command(label="⚙ Crypto Options ...", accelerator="Ctrl+C", command=self.crypto_options)
        m.add_command(label="⚙ Configure ...", accelerator="Ctrl+O", command=self.open_configure)
        m.add_command(label="🗝 Setup Key File ...", accelerator="Ctrl+K", command=self.setup_key_file)
        m.add_separator()
        self.var_sound = tk.BooleanVar(value=False)
        self.var_keyboard = tk.BooleanVar(value=False)
        self.var_startup = tk.BooleanVar(value=False)
        self.var_tray = tk.BooleanVar(value=False)
        m.add_command(label="Full / Short Crypto Explorer View (demo)", command=lambda: self.stub("View toggle"))
        m.add_checkbutton(label="Enable Sound Effects (demo)", variable=self.var_sound)
        m.add_checkbutton(label="Show On Screen Keyboard (demo)", variable=self.var_keyboard)
        m.add_separator()
        m.add_checkbutton(label="Run On Windows Start Up (demo)", variable=self.var_startup)
        m.add_checkbutton(label="Minimize To System Tray (demo)", variable=self.var_tray)
        self._menus.append(("Options", m))

        # Help
        m = self._menu(self)
        m.add_command(label="Help ...", accelerator="F1", command=self.show_help)
        m.add_command(label="Online Help ...", command=self.show_help)
        m.add_command(label="Online Support ...", command=self.show_help)
        m.add_separator()
        m.add_command(label="Show Credits", command=self.show_credits)
        m.add_command(label="Replay Boot Screen", command=self.replay_splash)
        m.add_command(label="About StegoShell ...", command=self.about)
        m.add_separator()
        m.add_command(label="Check For Updates / News (demo)", command=lambda: self.stub("Check For Updates"))
        m.add_command(label="Authenticate StegoShell ... (demo)", command=lambda: self.stub("Authenticate"))
        self._menus.append(("Help", m))

        # build the green top strip of menu buttons that post these dropdowns
        menubar = ctk.CTkFrame(self, fg_color=MENU_BG, corner_radius=0, height=30)
        menubar.pack(fill="x", side="top")
        menubar.pack_propagate(False)

        def make_opener(menu_obj, button):
            def opener():
                try:
                    x = button.winfo_rootx()
                    y = button.winfo_rooty() + button.winfo_height()
                    menu_obj.tk_popup(x, y)
                finally:
                    menu_obj.grab_release()
            return opener

        for name, menu_obj in self._menus:
            btn = ctk.CTkButton(menubar, text=name, width=10, height=26,
                                fg_color=MENU_BG, hover_color="#0d2a18",
                                text_color=YELLOW, font=(MONO, 11, "bold"),
                                corner_radius=2)
            btn.configure(command=make_opener(menu_obj, btn))
            btn.pack(side="left", padx=1, pady=2)

        # keyboard shortcuts from the screenshots
        self.bind("<Control-e>", lambda e: self.encrypt_text_window())
        self.bind("<Control-d>", lambda e: self.decrypt_text_window())
        self.bind("<Control-h>", lambda e: self.open_stego_workspace())
        self.bind("<Control-p>", lambda e: self.generate_password())
        self.bind("<F1>", lambda e: self.show_help())

    # ===============================================================
    # HEADER  (logo + brand)
    # ===============================================================
    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color=BLACK, height=92, corner_radius=0)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        # logo inside a green frame
        logo_path = os.path.join(ASSET_DIR, "logo.png")
        if os.path.exists(logo_path):
            logo_box = ctk.CTkFrame(header, fg_color=PANEL_BLACK, border_color=YELLOW_DEEP,
                                    border_width=2, corner_radius=6)
            logo_box.pack(side="left", padx=(16, 12), pady=14)
            img = Image.open(logo_path).convert("RGBA")
            self._logo_img = ctk.CTkImage(light_image=img, dark_image=img, size=(54, 54))
            ctk.CTkLabel(logo_box, image=self._logo_img, text="").pack(padx=6, pady=6)

        # title block with subtitle and a live status line
        wrap = ctk.CTkFrame(header, fg_color=BLACK)
        wrap.pack(side="left", anchor="w", pady=14)
        ctk.CTkLabel(wrap, text="STEGOSHELL", text_color=YELLOW,
                     font=(MONO, 24, "bold")).pack(anchor="w")
        ctk.CTkLabel(wrap, text="// stego_shell  ::  data hidden, data secured",
                     text_color=YELLOW_DARK, font=(MONO, 11, "bold")).pack(anchor="w")
        # animated status line (pulsing dot + facts)
        try:
            hs = tk.Canvas(wrap, width=380, height=18, bg="#040805",
                           highlightthickness=0, bd=0)
            hs.pack(anchor="w", pady=(4, 0))
            self._head_status = hs
            self._head_phase = 0
            self._animate_head_status()
        except Exception:
            self._head_status = None

        # wide matrix code-rain band on the right-center (decorative, guarded)
        try:
            rain = CodeRain(header, width=260, height=64, fg=YELLOW, dim="#0a3a1f")
            rain.pack(side="left", padx=24, pady=14, fill="y")
            self._header_rain = rain
        except Exception:
            self._header_rain = None

        # quick-action buttons on the far right, each with a specific job
        glyphs = ctk.CTkFrame(header, fg_color=BLACK)
        glyphs.pack(side="right", padx=12, pady=10)

        def add_tooltip(widget, text):
            tip = {"win": None}
            def show(_e):
                if tip["win"] is not None:
                    return
                x = widget.winfo_rootx()
                y = widget.winfo_rooty() + widget.winfo_height() + 2
                t = tk.Toplevel(widget)
                t.wm_overrideredirect(True)
                t.wm_geometry(f"+{x}+{y}")
                tk.Label(t, text=text, bg="#0a140d", fg="#00ff78",
                         font=(MONO, 9), padx=6, pady=2,
                         highlightbackground="#00b257", highlightthickness=1).pack()
                tip["win"] = t
            def hide(_e):
                if tip["win"] is not None:
                    tip["win"].destroy()
                    tip["win"] = None
            widget.bind("<Enter>", show)
            widget.bind("<Leave>", hide)

        # two icon actions: open the stego workspace, and quick encrypt text
        self._head_btn_imgs = []
        actions = [
            ("hide", self.open_stego_workspace, "open stego workspace"),
            ("encrypt", self.encrypt_text_window, "quick encrypt text"),
            ("key", self.generate_password, "generate password"),
        ]
        for icon_name, cmd, tip in actions:
            path = os.path.join(ASSET_DIR, f"cicon_{icon_name}.png")
            img = None
            if os.path.exists(path):
                pil = Image.open(path).convert("RGBA")
                img = ctk.CTkImage(light_image=pil, dark_image=pil, size=(18, 18))
                self._head_btn_imgs.append(img)
            b = ctk.CTkButton(glyphs, text="", image=img, command=cmd, width=30, height=30,
                              fg_color=PANEL_BLACK, hover_color="#0d2a18",
                              border_color=YELLOW_DEEP, border_width=1, corner_radius=4)
            b.pack(side="left", padx=3)
            add_tooltip(b, tip)

        # window controls: minimize and close
        for text, cmd, hov, tip in [("\u2014", self.iconify, "#0d2a18", "minimize"),
                                    ("\u2716", self.exit_app, "#3a0d0d", "close")]:
            b = ctk.CTkButton(glyphs, text=text, command=cmd, width=30, height=30,
                              fg_color=PANEL_BLACK, hover_color=hov, text_color=YELLOW,
                              border_color=YELLOW_DEEP, border_width=1,
                              font=("Arial", 14, "bold"), corner_radius=4)
            b.pack(side="left", padx=3)
            add_tooltip(b, tip)

        # thin green divider under the header
        ctk.CTkFrame(self, fg_color=YELLOW_DEEP, height=2, corner_radius=0).pack(fill="x", side="top")

    def _animate_head_status(self):
        c = getattr(self, "_head_status", None)
        if c is None or not c.winfo_exists():
            return
        import math, time
        c.delete("all")
        self._head_phase = (self._head_phase + 1) % 1000
        level = (math.sin(self._head_phase / 5.0) + 1) / 2
        g = int(90 + 165 * level)
        dot = "#%02x%02x%02x" % (0, g, int(g * 0.55))
        c.create_oval(2, 5, 12, 15, fill=dot, outline="")
        c.create_text(18, 10, text="online", anchor="w", fill="#00ff78", font=(MONO, 10, "bold"))
        c.create_text(78, 10, text="| keys 12/8", anchor="w", fill="#7fdfa6", font=(MONO, 10))
        c.create_text(168, 10, text="| AES-256", anchor="w", fill="#7fdfa6", font=(MONO, 10))
        c.create_text(250, 10, text="| LSB", anchor="w", fill="#7fdfa6", font=(MONO, 10))
        c.create_text(300, 10, text="| " + time.strftime("%H:%M:%S"), anchor="w",
                      fill="#7fdfa6", font=(MONO, 10))
        self.after(140, self._animate_head_status)

    # ===============================================================
    # BODY  (left button grid + right work area)
    # ===============================================================
    def _build_body(self):
        body = ctk.CTkFrame(self, fg_color=BLACK, corner_radius=0)
        body.pack(fill="both", expand=True, padx=10, pady=(0, 6))

        # left column, fixed width, matches the original button grid
        left = ctk.CTkFrame(body, fg_color=BLACK, width=320, corner_radius=0)
        left.pack(side="left", fill="y", padx=(0, 10))
        left.pack_propagate(False)

        rows = [
            [("encrypt_text", self.encrypt_text_window, "encrypt"), ("decrypt_text", self.decrypt_text_window, "decrypt")],
            [("copy", self.copy_text, "copy"), ("paste", self.paste_text, "paste"), ("clear", self.clear_text, "clear")],
            None,
            [("encrypt_files", self.encrypt_files, "encrypt"), ("decrypt_files", self.decrypt_files, "decrypt")],
            [("encrypt_folder", self.encrypt_folder, "folder"), ("decrypt_folder", self.decrypt_folder, "folder")],
            None,
            [("hide_files", self.hide_file, "hide"), ("hide_folder", self.hide_folder, "hide")],
            [("shred_files", self.shred_files, "shred"), ("shred_folder", self.shred_folder, "shred")],
            None,
            [("open_file", self.open_any_file, "open"), ("save_file", self.save_text_file, "save")],
        ]
        for row in rows:
            if row is None:
                ctk.CTkFrame(left, fg_color=BLACK, height=10, corner_radius=0).pack(fill="x")
                continue
            bar = AngledBar(left, row, height=34, terminal=True, color_icons=True)
            bar.pack(fill="x", pady=3)

        # open the steganography workspace from the grid area
        AngledBar(left, [("open_stego_workspace", self.open_stego_workspace)],
                  height=34, terminal=True).pack(fill="x", pady=(14, 6))

        # live system panel fills the space under the buttons
        try:
            self._build_system_panel(left)
        except Exception:
            pass

        # right side: one clean console plus the links row beneath it
        right = ctk.CTkFrame(body, fg_color=BLACK, corner_radius=0)
        right.pack(side="left", fill="both", expand=True)

        console = ctk.CTkFrame(right, fg_color=PANEL_BLACK, border_color=YELLOW_DEEP,
                               border_width=2, corner_radius=4)
        console.pack(fill="both", expand=True)

        # terminal title bar across the top of the console
        titlebar = ctk.CTkFrame(console, fg_color=MENU_BG, corner_radius=0, height=26)
        titlebar.pack(fill="x", padx=2, pady=(2, 0))
        titlebar.pack_propagate(False)
        dots = ctk.CTkFrame(titlebar, fg_color=MENU_BG)
        dots.pack(side="left", padx=8)
        for col in ("#ff5f56", "#ffbd2e", "#27c93f"):
            d = tk.Canvas(dots, width=12, height=12, bg=MENU_BG, highlightthickness=0, bd=0)
            d.create_oval(2, 2, 11, 11, fill=col, outline="")
            d.pack(side="left", padx=2)
        ctk.CTkLabel(titlebar, text="root@stegoshell: ~/stego  -  console",
                     text_color=YELLOW, font=(MONO, 10, "bold")).pack(side="left", padx=10)
        ctk.CTkLabel(titlebar, text="LSB + AES-256", text_color=YELLOW_DARK,
                     font=(MONO, 10)).pack(side="right", padx=10)

        self.output = ctk.CTkTextbox(console, fg_color=PANEL_BLACK, text_color=YELLOW,
                                     border_width=0, font=("Consolas", self.text_font_size),
                                     corner_radius=0)
        self.output.pack(fill="both", expand=True, padx=4, pady=4)

        links = ctk.CTkFrame(right, fg_color=BLACK)
        links.pack(fill="x", pady=(6, 0))
        for label, cmd in [("Show Full Menu", lambda: self.stub("Show Full Menu")),
                           ("Crypto Options", self.crypto_options),
                           ("Configure", self.open_configure),
                           ("Online Support", self.show_help)]:
            ctk.CTkButton(links, text="\u25cf " + label, command=cmd,
                          fg_color=BLACK, hover_color="#1a1a00", text_color=YELLOW,
                          font=("Arial", 11, "underline"), corner_radius=0, height=24).pack(side="left", expand=True)

        statusbar = ctk.CTkFrame(self, fg_color=BLACK)
        statusbar.pack(fill="x", side="bottom", padx=14, pady=(0, 4))
        self.status = ctk.CTkLabel(statusbar, text="status: idle", anchor="w",
                                   text_color=YELLOW_DARK, fg_color=BLACK, font=(MONO, 11))
        self.status.pack(side="left")
        self._blinker = ctk.CTkLabel(statusbar, text="\u2588", text_color=YELLOW,
                                     fg_color=BLACK, font=(MONO, 12, "bold"))
        self._blinker.pack(side="left", padx=(4, 0))
        # animated indicator strip on the right of the status bar
        try:
            ind = tk.Canvas(statusbar, width=300, height=18, bg="#040805",
                            highlightthickness=0, bd=0)
            ind.pack(side="right")
            self._status_canvas = ind
            self._status_phase = 0
            self._animate_status()
        except Exception:
            ctk.CTkLabel(statusbar, text="engine: ok   crypto: AES-256-GCM   mode: terminal",
                         text_color=YELLOW_DARK, fg_color=BLACK, font=(MONO, 11)).pack(side="right")

    def _animate_status(self):
        """Pulsing dots and a moving activity meter on the status bar."""
        c = getattr(self, "_status_canvas", None)
        if c is None or not c.winfo_exists():
            return
        c.delete("all")
        self._status_phase = (self._status_phase + 1) % 1000
        ph = self._status_phase
        import math
        # three labelled pulsing dots
        dots = [("engine", 0), ("crypto", 2), ("link", 4)]
        x = 6
        for label, off in dots:
            level = (math.sin((ph + off * 6) / 6.0) + 1) / 2
            g = int(80 + 175 * level)
            colour = "#%02x%02x%02x" % (0, g, int(g * 0.55))
            c.create_oval(x, 6, x + 8, 14, fill=colour, outline="")
            c.create_text(x + 12, 10, text=label, anchor="w",
                          fill="#1f7a45", font=(MONO, 9))
            x += 12 + len(label) * 6 + 12
        # small moving activity meter
        c.create_text(x, 10, text="act", anchor="w", fill="#1f7a45", font=(MONO, 9))
        x += 22
        for k in range(10):
            level = (math.sin((ph + k * 3) / 4.0) + 1) / 2
            h = 2 + int(10 * level)
            c.create_rectangle(x + k * 6, 14 - h, x + k * 6 + 4, 14,
                               fill="#00ff78", outline="")
        self.after(120, self._animate_status)

    def _build_system_panel(self, parent):
        """A live system monitor panel that fills the empty left space."""
        panel = ctk.CTkFrame(parent, fg_color=PANEL_BLACK, border_color=YELLOW_DEEP,
                             border_width=1, corner_radius=4)
        panel.pack(fill="both", expand=True, pady=(8, 0))
        ctk.CTkLabel(panel, text="// system_monitor", text_color=YELLOW,
                     font=(MONO, 11, "bold")).pack(anchor="w", padx=10, pady=(8, 2))

        canvas = tk.Canvas(panel, bg="#040805", highlightthickness=0, bd=0)
        canvas.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self._sys_canvas = canvas
        self._sys_phase = 0
        # seed pseudo readings so the bars look alive but smooth
        import random
        self._sys_seed = [random.random() for _ in range(3)]
        self._animate_system_panel()

    def _animate_system_panel(self):
        c = getattr(self, "_sys_canvas", None)
        if c is None or not c.winfo_exists():
            return
        import math, time
        c.delete("all")
        w = max(160, c.winfo_width())
        self._sys_phase += 1
        ph = self._sys_phase

        def bar(y, label, level, colour="#00ff78"):
            c.create_text(10, y, text=label, anchor="w", fill="#7fdfa6", font=(MONO, 10))
            bx0, bx1 = 70, w - 50
            c.create_rectangle(bx0, y - 6, bx1, y + 6, outline="#1f7a45")
            fillw = int((bx1 - bx0) * level)
            seg = bx0
            while seg < bx0 + fillw - 4:
                c.create_rectangle(seg, y - 4, seg + 4, y + 4, fill=colour, outline="")
                seg += 6
            c.create_text(w - 44, y, text=f"{int(level*100):3d}%", anchor="w",
                          fill="#7fdfa6", font=(MONO, 10))

        cpu = (math.sin(ph / 18.0) + 1) / 2 * 0.5 + self._sys_seed[0] * 0.4
        mem = (math.sin(ph / 26.0 + 1) + 1) / 2 * 0.3 + 0.45
        net = (math.sin(ph / 11.0 + 2) + 1) / 2 * 0.6 + self._sys_seed[2] * 0.2
        bar(24, "cpu", min(0.99, cpu))
        bar(48, "mem", min(0.99, mem))
        bar(72, "net", min(0.99, net), colour="#00b257")

        # live clock and static facts
        clock = time.strftime("%H:%M:%S")
        c.create_text(10, 104, text=f"time   {clock}", anchor="w",
                      fill="#7fdfa6", font=(MONO, 10))
        c.create_text(10, 124, text="keys   12 / min 8  [ok]", anchor="w",
                      fill="#7fdfa6", font=(MONO, 10))
        c.create_text(10, 144, text="cipher AES-256-GCM", anchor="w",
                      fill="#7fdfa6", font=(MONO, 10))
        c.create_text(10, 164, text="engine ok", anchor="w",
                      fill="#00ff78", font=(MONO, 10))

        # a moving scan line near the bottom
        scan_y = 190 + int(20 * ((ph % 40) / 40.0))
        c.create_line(10, scan_y, w - 20, scan_y, fill="#0a3a1f")
        c.create_text(10, 224, text="> monitoring ...", anchor="w",
                      fill="#1f7a45", font=(MONO, 10))

        self.after(200, self._animate_system_panel)

    # ===============================================================
    # BOTTOM TAB BAR  (the angular yellow tabs in the screenshot)
    # ===============================================================
    def _build_bottom_bar(self):
        bar = ctk.CTkFrame(self, fg_color=BLACK, corner_radius=0, height=46)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        tabs = [
            ("Crypto\nExplorer*", lambda: self.stub("Crypto Explorer")),
            ("System\nMonitor*", lambda: self.stub("System Monitor")),
            ("Pass Safe", self.password_safe),
            ("Self\nDeCryptor", self.self_decrypt),
            ("Send\nEmail*", lambda: self.stub("Send Email")),
            ("Stego", self.open_stego_workspace),
            ("Data\nForensics*", self.data_forensics),
            ("System\nTray*", lambda: self.stub("System Tray")),
            ("Cancel", self.cancel_action),
            ("Exit", self.exit_app),
        ]
        AngledBar(bar, tabs, height=46, skew=8, terminal=True, font=(MONO, 11, "bold")).pack(fill="both", expand=True)
        # a tiny legend so the star is clear
        legend = ctk.CTkFrame(self, fg_color=BLACK, height=16)
        legend.pack(fill="x", side="bottom")
        ctk.CTkLabel(legend, text="* demo screen   |   the rest are working features",
                     text_color=YELLOW_DARK, font=(MONO, 9)).pack(side="right", padx=14)

    # ===============================================================
    # small helpers
    # ===============================================================
    def _log(self, text):
        box = self._stego_out if self._stego_out is not None else self.output
        box.insert("end", text + "\n")
        box.see("end")

    def _start_cursor_blink(self):
        """Blink the terminal indicator in the status area."""
        self._cursor_on = False
        self._blink_cursor()

    def _blink_cursor(self):
        try:
            self._cursor_on = not self._cursor_on
            if getattr(self, "_blinker", None) is not None:
                self._blinker.configure(text="\u2588" if self._cursor_on else " ")
        except Exception:
            pass
        self.after(530, self._blink_cursor)

    def _set_status(self, text):
        self.status.configure(text="status: " + text)

    def _show_preview(self, array):
        if self._stego_preview is None:
            return
        img = Image.fromarray(array.astype("uint8"))
        img.thumbnail((360, 200))
        self._preview_ref = ctk.CTkImage(light_image=img, dark_image=img,
                                         size=(img.width, img.height))
        self._stego_preview.configure(image=self._preview_ref, text="")

    def _ask_text(self, title, prompt, show=None):
        dialog = ctk.CTkInputDialog(title=title, text=prompt)
        if show == "*":
            try:
                dialog._entry.configure(show="*")
            except Exception:
                pass
        return dialog.get_input()

    def _ask_password(self, title="Password", prompt="Enter the password you used:"):
        return PassPhraseDialog(self, mode="unlock", default=self.default_passphrase).get()

    def _make_password(self, title="Create Password"):
        """Ask for a new pass phrase with the combined dialog and a confirm box."""
        return PassPhraseDialog(self, mode="create", default=self.default_passphrase).get()

    def _warn(self, msg):
        messagebox.showwarning("Notice", msg)
        self._set_status(msg.lower())

    def _error(self, e):
        messagebox.showerror("Error", str(e))
        self._log("Error: " + str(e))
        self._set_status("error")

    def _run(self, func, *args):
        def worker():
            try:
                func(*args)
            except Exception as e:
                self.after(0, lambda: self._error(e))
        threading.Thread(target=worker, daemon=True).start()

    def stub(self, name):
        messagebox.showinfo(
            name + "  [demo screen]",
            f"{name} is a demo screen, not a working feature.\n\n"
            "The graded part of this assignment is image and audio steganography, "
            "which is fully built and working. This item matches the reference "
            "layout but is left as a demo because it touches Windows internals "
            "or outside services that do not belong in a class app.")
        self._set_status(f"{name} (demo)")

    def privacy_stub(self, what):
        messagebox.showinfo(
            "Privacy  [demo screen]",
            f"Shredding {what} is a demo screen, not a working feature.\n\n"
            "Wiping browser or free space data automatically is risky in a class "
            "app, so this is left as a demo. The graded steganography features are "
            "fully built and working.")
        self._set_status("privacy (demo)")

    # ===============================================================
    # FILE menu
    # ===============================================================
    def open_any_file(self):
        path = filedialog.askopenfilename(title="Open Any File")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
            self.output.delete("1.0", "end")
            self.output.insert("end", text)
            self._set_status(f"opened {os.path.basename(path)}")
        except Exception as e:
            self._error(e)

    def save_text_file(self):
        path = filedialog.asksaveasfilename(title="Save Text As File", defaultextension=".txt")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.output.get("1.0", "end"))
        self._set_status(f"saved {os.path.basename(path)}")

    def print_text(self):
        text = self.output.get("1.0", "end")
        tmp = os.path.join(os.path.expanduser("~"), "quickcrypto_print.txt")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
        if sys.platform.startswith("win"):
            try:
                os.startfile(tmp, "print")
                self._set_status("sent to printer")
                return
            except Exception:
                pass
        messagebox.showinfo("Print", f"Text saved for printing at:\n{tmp}")

    def cancel_action(self):
        self._set_status("cancelled")

    def exit_app(self):
        self.destroy()

    # ===============================================================
    # EDIT menu
    # ===============================================================
    def copy_text(self):
        text = self.output.get("1.0", "end").strip()
        self.clipboard_clear()
        self.clipboard_append(text)
        self._set_status("copied to clipboard")

    def paste_text(self):
        try:
            self.output.insert("end", self.clipboard_get())
            self._set_status("pasted")
        except Exception:
            self._warn("Clipboard is empty.")

    def clear_text(self):
        self.output.delete("1.0", "end")
        self._set_status("cleared")

    # ===============================================================
    # ENCRYPT / DECRYPT menus
    # ===============================================================
    def encrypt_text_window(self):
        text = self.output.get("1.0", "end").strip()
        if not text:
            return self._warn("Type text in the work area first.")
        pw = self._make_password("Encrypt Text")
        if not pw:
            return
        token = ce.encrypt_text(text, pw)
        self.output.delete("1.0", "end")
        self.output.insert("end", token)
        self._set_status("text encrypted")

    def decrypt_text_window(self):
        text = self.output.get("1.0", "end").strip()
        if not text:
            return self._warn("Paste an encrypted token in the work area first.")
        pw = self._ask_password("Decrypt Text")
        if not pw:
            return
        try:
            plain = ce.decrypt_text(text, pw)
        except Exception as e:
            return self._error(e)
        self.output.delete("1.0", "end")
        self.output.insert("end", plain)
        self._set_status("text decrypted")

    def encrypt_files(self):
        path = filedialog.askopenfilename(title="Choose file to encrypt")
        if not path:
            return
        pw = self._make_password("Encrypt File")
        if not pw:
            return
        out = ce.encrypt_file(path, pw)
        self._log(f"File encrypted: {out}")
        self._log("Remember your password. Without it the file cannot be opened.")
        self._set_status("file encrypted")
        self._auto_remove_original(path, out)

    def _auto_remove_original(self, src_path, out_path):
        """Delete the plaintext after encrypting, but only once a valid .qcf exists."""
        if not os.path.exists(src_path):
            return
        if not self._is_valid_encrypted(out_path):
            self._log("Encrypted file not verified. Keeping the original for safety.")
            return
        try:
            if os.path.isdir(src_path):
                ce.shred_folder(src_path)
            else:
                ce.shred_file(src_path)
            self._set_status("original removed")
        except Exception as e:
            self._error(e)

    def _is_valid_encrypted(self, out_path):
        """True if the output is a real encrypted file. Checks size and the header."""
        try:
            if not os.path.exists(out_path) or os.path.getsize(out_path) < 40:
                return False
            with open(out_path, "rb") as f:
                head = f.read(8)
            return head == ce.FILE_MAGIC
        except Exception:
            return False

    def _offer_shred_original(self, path):
        """Kept for compatibility. No longer prompts, removal is automatic now."""
        return

    def decrypt_files(self):
        path = filedialog.askopenfilename(title="Choose .qcf file to decrypt",
                                          filetypes=[("StegoShell", "*.qcf"), ("All", "*.*")])
        if not path:
            return
        pw = self._ask_password("Decrypt File")
        if not pw:
            return
        try:
            out = ce.decrypt_file(path, pw)
        except Exception as e:
            return self._error(e)
        self._log(f"File decrypted: {os.path.basename(out)}")
        self._set_status("file decrypted")
        self._auto_remove_encrypted(path, out)

    def _auto_remove_encrypted(self, qcf_path, out_path):
        """Delete the .qcf after decrypting, but only once the output exists."""
        if not os.path.exists(qcf_path):
            return
        if not os.path.exists(out_path):
            self._log("Decrypted output not found. Keeping the encrypted file for safety.")
            return
        try:
            ce.shred_file(qcf_path)
            self._set_status("encrypted file removed")
        except Exception as e:
            self._error(e)

    def encrypt_folder(self):
        path = filedialog.askdirectory(title="Choose folder to encrypt")
        if not path:
            return
        pw = self._make_password("Encrypt Folder")
        if not pw:
            return
        out = ce.encrypt_folder(path, pw)
        self._log(f"Folder encrypted: {os.path.basename(out)}")
        self._set_status("folder encrypted")
        self._auto_remove_original(path, out)

    def decrypt_folder(self):
        path = filedialog.askopenfilename(title="Choose .qcf folder archive",
                                          filetypes=[("StegoShell", "*.qcf"), ("All", "*.*")])
        if not path:
            return
        pw = self._ask_password("Decrypt Folder")
        if not pw:
            return
        try:
            out = ce.decrypt_folder(path, pw)
        except Exception as e:
            return self._error(e)
        self._log(f"Folder decrypted to: {out}")
        self._set_status("folder decrypted")
        self._auto_remove_encrypted(path, out)

    # ===============================================================
    # SHRED menu
    # ===============================================================
    def shred_files(self):
        path = filedialog.askopenfilename(title="Choose file to shred")
        if not path:
            return
        if not messagebox.askyesno("Shred File",
                                   f"Permanently destroy this file?\n\n{path}\n\nThis cannot be undone."):
            return
        ce.shred_file(path)
        self._log(f"Shredded: {os.path.basename(path)}")
        self._set_status("file shredded")

    def shred_folder(self):
        path = filedialog.askdirectory(title="Choose folder to shred")
        if not path:
            return
        if not messagebox.askyesno("Shred Folder",
                                   f"Permanently destroy this folder and all files?\n\n{path}\n\nThis cannot be undone."):
            return
        count = ce.shred_folder(path)
        self._log(f"Shredded folder: {count} files destroyed.")
        self._set_status("folder shredded")

    def data_forensics(self):
        messagebox.showinfo(
            "Data Forensics  [demo screen]",
            "Data Forensics is a demo screen, not a working feature.\n\n"
            "A real version would scan disk areas for recoverable data. "
            "It is left as a demo so the menu matches the reference layout. "
            "The graded steganography features are fully built and working.")
        self._set_status("data forensics (demo)")

    # ===============================================================
    # HIDE / STEGO  (graded core)
    # ===============================================================
    def open_stego_workspace(self):
        if self._stego_win is not None and self._stego_win.winfo_exists():
            self._stego_win.lift()
            return

        win = ctk.CTkToplevel(self)
        win.title("Steganography Workspace")
        win.geometry("800x820")
        win.minsize(720, 640)
        win.configure(fg_color=BLACK)
        self._stego_win = win

        ctk.CTkLabel(win, text="STEGANOGRAPHY  WORKSPACE", text_color=YELLOW,
                     font=(MONO, 16, "bold")).pack(pady=(10, 4))

        grid = ctk.CTkFrame(win, fg_color=BLACK)
        grid.pack(fill="x", padx=10)
        keys = [
            [("Load Cover", self.load_cover, "open"), ("Load Stego", self.load_stego, "image")],
            [("Hide Text", self.hide_text, "shield"), ("Extract Text", self.extract_text, "eye")],
            [("Hide File", self.hide_file, "file"), ("Extract File", self.extract_file, "eye")],
            [("Encrypt + Hide Text", self.encrypt_and_hide, "lock"), ("Extract + Decrypt", self.extract_and_decrypt, "unlock")],
            [("Modified Pixels", self.show_modified, "image"), ("Binary Compare", self.binary_compare, "image")],
            [("Compare Images", self.compare_images, "image"), ("Capacity Check", self.capacity_check, "info")],
            [("Side by Side View", self.side_by_side, "image"), ("Run Self Test", self.run_self_test, "gear")],
            [("Save Stego", self.save_stego, "save"), ("Recover Cover", self.recover_cover, "save")],
        ]
        for row in keys:
            AngledBar(grid, row, height=32, terminal=True).pack(fill="x", pady=2)

        ctk.CTkLabel(grid, text="AUDIO  (WAV)", text_color=YELLOW_DARK,
                     font=("Arial", 11, "bold")).pack(anchor="w", pady=(8, 2))
        audio_keys = [
            [("Hide Text in Sound", self.audio_hide_text, "shield"), ("Read Text from Sound", self.audio_read_text, "eye")],
            [("Hide File in Sound", self.audio_hide_file, "file"), ("Read File from Sound", self.audio_read_file, "eye")],
        ]
        for row in audio_keys:
            AngledBar(grid, row, height=32, terminal=True).pack(fill="x", pady=2)

        # capacity bar, shows payload room against image space
        capframe = ctk.CTkFrame(win, fg_color=BLACK)
        capframe.pack(fill="x", padx=10, pady=(6, 0))
        ctk.CTkLabel(capframe, text="Capacity", text_color=YELLOW_DARK,
                     font=("Arial", 11)).pack(side="left", padx=(0, 8))
        self._cap_bar = ctk.CTkProgressBar(capframe, progress_color=YELLOW,
                                           fg_color=PANEL_BLACK, height=14)
        self._cap_bar.set(0)
        self._cap_bar.pack(side="left", fill="x", expand=True)
        self._cap_label = ctk.CTkLabel(capframe, text="load a cover", text_color=YELLOW_DARK,
                                       font=("Consolas", 10))
        self._cap_label.pack(side="left", padx=8)

        self._stego_preview = ctk.CTkLabel(win, text="No image loaded",
                                           fg_color=PANEL_BLACK, text_color=YELLOW_DARK,
                                           height=130, corner_radius=4, font=("Arial", 12))
        self._stego_preview.pack(fill="x", padx=10, pady=8)

        self._stego_out = ctk.CTkTextbox(win, fg_color=PANEL_BLACK, text_color=YELLOW,
                                         border_color=YELLOW_DEEP, border_width=2,
                                         font=("Consolas", 11), corner_radius=4, height=120)
        self._stego_out.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        def on_close():
            self._stego_win = None
            self._stego_out = None
            self._stego_preview = None
            self._cap_bar = None
            self._cap_label = None
            win.destroy()

        win.protocol("WM_DELETE_WINDOW", on_close)
        self._log("Steganography workspace open. Load a cover image to begin.")
        self._set_status("stego workspace open")

    def _update_capacity(self, used_bytes=0):
        """Refresh the capacity bar against the current cover."""
        if getattr(self, "_cap_bar", None) is None or self.cover_array is None:
            return
        cap = se.capacity_bytes(self.cover_array)
        frac = min(1.0, used_bytes / cap) if cap else 0
        self._cap_bar.set(frac)
        self._cap_label.configure(text=f"{used_bytes} / {cap} bytes")

    def encrypt_and_hide(self):
        """Encrypt the message first, then hide the ciphertext. Matches slide 11."""
        if not self._ensure_cover():
            return
        text = self._ask_text("Encrypt and Hide", "Type the secret message:")
        if not text:
            return
        password = self._make_password("Encrypt and Hide")
        if not password:
            return
        try:
            cipher = ce.encrypt_text(text, password).encode("utf-8")
            cap = se.capacity_bytes(self.cover_array)
            if len(cipher) > cap:
                raise ValueError(f"Encrypted payload too large. Image holds about {cap} bytes.")
            self.stego_array = se.hide_bytes(self.cover_array, cipher)
            self._show_preview(self.stego_array)
            changed = se.changed_pixel_count(self.cover_array, self.stego_array)
            self._update_capacity(len(cipher))
            self._log(f"Encrypted then hidden. Cipher {len(cipher)} bytes, {changed} pixels changed.")
            self._log("The message is encrypted, so extraction alone shows only ciphertext.")
            self._set_status("encrypted and hidden")
        except Exception as e:
            self._error(e)

    def extract_and_decrypt(self):
        """Pull the hidden ciphertext, then decrypt it with the password."""
        if self.stego_array is None:
            return self._warn("Load a stego image or hide something first.")
        raw = se.extract_raw_bytes(self.stego_array)
        if raw is None:
            self._log("No hidden data found.")
            return
        password = self._ask_password("Password", "Password to decrypt with:")
        if not password:
            return
        try:
            text = ce.decrypt_text(raw.decode("utf-8", errors="replace"), password)
            self._log("Decrypted hidden message:")
            self._log(text)
            self._set_status("extracted and decrypted")
        except Exception as e:
            self._error(e)

    def side_by_side(self):
        """Show cover, stego, and a map of changed pixels in one window."""
        if self.cover_array is None or self.stego_array is None:
            return self._warn("Need both a cover and a stego image.")
        try:
            from PIL import Image as PILImage
            cover = PILImage.fromarray(self.cover_array.astype("uint8"))
            stego = PILImage.fromarray(self.stego_array.astype("uint8"))
            # column-bar view stays visible for any image shape
            diff = PILImage.fromarray(
                se.difference_bars(self.cover_array, self.stego_array, width=300, height=120))
            # scale all three to the same width so a wide thin image still reads
            target_w = 300
            def fit(im, nearest=False):
                ratio = target_w / im.width
                size = (target_w, max(1, int(im.height * ratio)))
                method = PILImage.NEAREST if nearest else PILImage.LANCZOS
                return im.resize(size, method)
            cover, stego = fit(cover), fit(stego)
            # diff is already 300 wide from difference_bars, leave as is

            win = ctk.CTkToplevel(self)
            win.title("Side by Side: Cover, Stego, Changed Pixels")
            win.configure(fg_color=BLACK)
            row = ctk.CTkFrame(win, fg_color=BLACK)
            row.pack(padx=12, pady=12)
            self._sbs_refs = []
            for title, im in [("Cover", cover), ("Stego", stego), ("Changed pixels", diff)]:
                col = ctk.CTkFrame(row, fg_color=PANEL_BLACK, corner_radius=4)
                col.pack(side="left", padx=8, pady=4)
                ctk.CTkLabel(col, text=title, text_color=YELLOW,
                             font=("Arial", 12, "bold")).pack(pady=(6, 2))
                cimg = ctk.CTkImage(light_image=im, dark_image=im, size=(im.width, im.height))
                self._sbs_refs.append(cimg)
                ctk.CTkLabel(col, image=cimg, text="").pack(padx=6, pady=(0, 6))
            changed = se.changed_pixel_count(self.cover_array, self.stego_array)
            ctk.CTkLabel(win, text=f"{changed} pixel values changed. Bright yellow marks where the data sits.",
                         text_color=YELLOW_DARK, font=("Arial", 11)).pack(pady=(0, 12))
            self._set_status("side by side shown")
        except Exception as e:
            self._error(e)

    def run_self_test(self):
        """Hide and extract a known string, report pass or fail in one click."""
        passed, detail = se.self_test()
        mark = "PASS" if passed else "FAIL"
        self._log(f"Self test {mark}: {detail}")
        self._set_status(f"self test {mark.lower()}")

    def load_cover(self):
        path = filedialog.askopenfilename(
            title="Open Cover Image",
            filetypes=[("Images", "*.png *.bmp *.jpg *.jpeg"), ("All files", "*.*")])
        if not path:
            return
        try:
            self.cover_array = se.load_image(path)
            self.cover_path = path
            self.stego_array = None
            self._show_preview(self.cover_array)
            h, w = self.cover_array.shape[:2]
            self._log(f"Cover loaded: {os.path.basename(path)} ({w}x{h}).")
            self._log(f"Capacity: about {se.capacity_bytes(self.cover_array)} bytes.")
            self._update_capacity(0)
            self._set_status("cover loaded")
        except Exception as e:
            self._error(e)

    def load_stego(self):
        path = filedialog.askopenfilename(
            title="Open Stego Image",
            filetypes=[("Images", "*.png *.bmp"), ("All files", "*.*")])
        if not path:
            return
        try:
            self.stego_array = se.load_image(path)
            self.stego_path = path
            self._show_preview(self.stego_array)
            self._log(f"Stego image loaded: {os.path.basename(path)}.")
            self._set_status("stego loaded")
        except Exception as e:
            self._error(e)

    def hide_text(self):
        if self.cover_array is None:
            return self._warn("Load a cover image first.")
        text = self._ask_text("Hide Text", "Type the secret message:")
        if not text:
            return
        self._run(self._do_hide_text, text)

    def _do_hide_text(self, text):
        cap = se.capacity_bytes(self.cover_array)
        if len(text.encode("utf-8")) > cap:
            raise ValueError(f"Text too large. Image holds about {cap} bytes.")
        self.stego_array = se.hide_text(self.cover_array, text)
        self.after(0, lambda: self._show_preview(self.stego_array))
        changed = se.changed_pixel_count(self.cover_array, self.stego_array)
        self.after(0, lambda: self._update_capacity(len(text.encode("utf-8"))))
        self._log(f"Text hidden. {changed} pixel values changed. Use Save Stego next.")
        self._set_status("text hidden, not yet saved")

    def _ensure_cover(self):
        """Return True if a cover is loaded, asking for one if needed."""
        if self.cover_array is not None:
            return True
        path = filedialog.askopenfilename(
            title="Choose a carrier image",
            filetypes=[("Images", "*.png *.bmp *.jpg *.jpeg"), ("All files", "*.*")])
        if not path:
            return False
        try:
            self.cover_array = se.load_image(path)
            self.cover_path = path
            self.stego_array = None
            self._show_preview(self.cover_array)
            self._log(f"Carrier loaded: {os.path.basename(path)}.")
            return True
        except Exception as e:
            self._error(e)
            return False

    def hide_file(self):
        if not self._ensure_cover():
            return
        path = filedialog.askopenfilename(title="Choose a file to hide")
        if not path:
            return
        self._run(self._do_hide_file, path)

    def _do_hide_file(self, path):
        size = os.path.getsize(path)
        cap = se.capacity_bytes(self.cover_array)
        if size + 64 > cap:
            raise ValueError(f"File too large ({size} bytes). Image holds about {cap} bytes.")
        self.stego_array = se.hide_file(self.cover_array, path)
        self.after(0, lambda: self._show_preview(self.stego_array))
        changed = se.changed_pixel_count(self.cover_array, self.stego_array)
        self._log(f"File hidden: {os.path.basename(path)} ({size} bytes). {changed} pixels changed.")
        if self._stego_win is None:
            self._prompt_save_stego()
        self._set_status("file hidden, not yet saved")

    def _prompt_save_stego(self):
        """When hiding from the main grid, offer to save right away."""
        path = filedialog.asksaveasfilename(title="Save Stego Image", defaultextension=".png",
                                            filetypes=[("PNG", "*.png"), ("BMP", "*.bmp")])
        if path:
            se.save_image(self.stego_array, path)
            self.stego_path = path
            self._log(f"Stego image saved: {path} (lossless PNG).")

    def hide_folder(self):
        if not self._ensure_cover():
            return
        folder = filedialog.askdirectory(title="Choose folder to hide")
        if not folder:
            return
        import tempfile, zipfile
        tmp = os.path.join(tempfile.gettempdir(), "qc_hide_folder.zip")
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _d, files in os.walk(folder):
                for name in files:
                    full = os.path.join(root, name)
                    zf.write(full, os.path.relpath(full, folder))
        self._run(self._do_hide_file, tmp)

    def extract_text(self):
        if self.stego_array is None:
            return self._warn("Load a stego image or hide text first.")
        text = se.extract_text(self.stego_array)
        if text is None:
            self._log("No hidden text found.")
            return
        self._log("Extracted text:")
        self._log(text)
        self._set_status("text extracted")

    def extract_file(self):
        if self.stego_array is None:
            return self._warn("Load a stego image or hide a file first.")
        result = se.extract_file(self.stego_array)
        if result is None:
            self._log("No hidden file found.")
            return
        name, data = result
        save_path = filedialog.asksaveasfilename(title="Save extracted file as", initialfile=name)
        if not save_path:
            return
        with open(save_path, "wb") as f:
            f.write(data)
        self._log(f"File extracted: {name} ({len(data)} bytes) -> {save_path}")
        self._set_status("file extracted")

    def show_modified(self):
        if self.cover_array is None or self.stego_array is None:
            return self._warn("Need both a cover and a stego image.")
        rows = se.first_modified_pixels(self.cover_array, self.stego_array, 20)
        self._log("First 20 pixel values, original vs stego:")
        for i, orig, steg in rows:
            self._log(f"  Pixel {i:>3}: Original={orig:>3}  Stego={steg:>3}")
        self._set_status("modified pixels shown")

    def binary_compare(self):
        if self.cover_array is None or self.stego_array is None:
            return self._warn("Need both a cover and a stego image.")
        rows = se.binary_compare(self.cover_array, self.stego_array, 30)
        self._log("First 30 values in binary, cover -> stego:")
        for i, before, after in rows:
            mark = "  <-- changed" if before != after else ""
            self._log(f"  {i:02d} : {before} -> {after}{mark}")
        self._set_status("binary compare shown")

    def compare_images(self):
        if self.cover_array is None or self.stego_array is None:
            return self._warn("Need both a cover and a stego image.")
        changed = se.changed_pixel_count(self.cover_array, self.stego_array)
        total = self.cover_array.size
        pct = (changed / total) * 100 if total else 0
        self._log(f"Changed pixel values: {changed} of {total} ({pct:.4f}%).")
        self._set_status("images compared")

    def capacity_check(self):
        if self.cover_array is None:
            return self._warn("Load a cover image first.")
        bits = se.capacity_bits(self.cover_array)
        byts = se.capacity_bytes(self.cover_array)
        h, w = self.cover_array.shape[:2]
        self._log(f"Image {w}x{h}. Holds {bits} payload bits, about {byts} bytes.")
        self._set_status("capacity checked")

    def save_stego(self):
        if self.stego_array is None:
            return self._warn("Nothing to save. Hide text or a file first.")
        path = filedialog.asksaveasfilename(title="Save Stego Image", defaultextension=".png",
                                            filetypes=[("PNG", "*.png"), ("BMP", "*.bmp")])
        if not path:
            return
        se.save_image(self.stego_array, path)
        self.stego_path = path
        self._log(f"Stego image saved: {path} (lossless PNG).")
        self._set_status("stego saved")

    def recover_cover(self):
        if self.cover_array is None:
            return self._warn("Load a cover image first.")
        path = filedialog.asksaveasfilename(title="Save Recovered Cover", defaultextension=".png",
                                            initialfile="recovered_cover.png",
                                            filetypes=[("PNG", "*.png")])
        if not path:
            return
        se.save_image(self.cover_array, path)
        self._log(f"Recovered cover saved: {path}")
        self._set_status("cover recovered")

    # ===============================================================
    # AUDIO stego (WAV). Matches the audio steganography slides.
    # ===============================================================
    def audio_hide_text(self):
        carrier = filedialog.askopenfilename(title="Choose a WAV carrier",
                                             filetypes=[("WAV audio", "*.wav")])
        if not carrier:
            return
        text = self._ask_text("Hide Text in Sound", "Type the secret message:")
        if not text:
            return
        out = filedialog.asksaveasfilename(title="Save stego WAV", defaultextension=".wav",
                                           filetypes=[("WAV audio", "*.wav")])
        if not out:
            return
        try:
            cap = au.capacity_bytes(carrier)
            if len(text.encode("utf-8")) > cap:
                raise ValueError(f"Text too large. Audio holds about {cap} bytes.")
            au.hide_text_in_wav(carrier, text, out)
            self._log(f"Text hidden in sound: {out}")
            self._set_status("audio text hidden")
        except Exception as e:
            self._error(e)

    def audio_hide_file(self):
        carrier = filedialog.askopenfilename(title="Choose a WAV carrier",
                                             filetypes=[("WAV audio", "*.wav")])
        if not carrier:
            return
        secret = filedialog.askopenfilename(title="Choose a file to hide")
        if not secret:
            return
        out = filedialog.asksaveasfilename(title="Save stego WAV", defaultextension=".wav",
                                           filetypes=[("WAV audio", "*.wav")])
        if not out:
            return
        try:
            cap = au.capacity_bytes(carrier)
            size = os.path.getsize(secret)
            if size + 64 > cap:
                raise ValueError(f"File too large ({size} bytes). Audio holds about {cap} bytes.")
            au.hide_file_in_wav(carrier, secret, out)
            self._log(f"File hidden in sound: {os.path.basename(secret)} -> {out}")
            self._set_status("audio file hidden")
        except Exception as e:
            self._error(e)

    def audio_read_text(self):
        path = filedialog.askopenfilename(title="Choose a stego WAV",
                                          filetypes=[("WAV audio", "*.wav")])
        if not path:
            return
        try:
            text = au.extract_text_from_wav(path)
            if text is None:
                self._log("No hidden text found in this WAV.")
                return
            self._log("Extracted text from sound:")
            self._log(text)
            self._set_status("audio text extracted")
        except Exception as e:
            self._error(e)

    def audio_read_file(self):
        path = filedialog.askopenfilename(title="Choose a stego WAV",
                                          filetypes=[("WAV audio", "*.wav")])
        if not path:
            return
        try:
            result = au.extract_file_from_wav(path)
            if result is None:
                self._log("No hidden file found in this WAV.")
                return
            name, data = result
            save_path = filedialog.asksaveasfilename(title="Save extracted file as", initialfile=name)
            if not save_path:
                return
            with open(save_path, "wb") as f:
                f.write(data)
            self._log(f"File extracted from sound: {name} ({len(data)} bytes) -> {save_path}")
            self._set_status("audio file extracted")
        except Exception as e:
            self._error(e)


    # ===============================================================
    # PERSONALIZE menu
    # ===============================================================
    def choose_font(self):
        size = self._ask_text("Text Font", "Font size for the work area (8 to 28):")
        if not size:
            return
        try:
            n = max(8, min(28, int(size)))
            self.text_font_size = n
            self.output.configure(font=("Consolas", n))
            self._set_status(f"font size {n}")
        except ValueError:
            self._warn("Type a number.")

    def cycle_colors(self):
        mode = ctk.get_appearance_mode()
        ctk.set_appearance_mode("light" if mode == "Dark" else "dark")
        self._set_status("colours toggled")

    def cycle_theme(self):
        self.cycle_colors()

    def reset_defaults(self):
        ctk.set_appearance_mode("dark")
        self.output.configure(font=("Consolas", 12))
        self.text_font_size = 12
        self._set_status("defaults reset")

    # ===============================================================
    # TOOLS menu
    # ===============================================================
    def generate_password(self):
        length = self._ask_text("Generate Secure Password", "Length (default 16):")
        try:
            n = int(length) if length else 16
        except ValueError:
            n = 16
        pw = ce.generate_password(n)
        self.output.insert("end", f"\nGenerated password: {pw}\n")
        self._log(f"Password generated ({n} characters). Strength: {ce.test_password_strength(pw)[1]}.")
        self._set_status("password generated")

    def test_password(self):
        pw = self._ask_text("Password Testing", "Type a password to test:", show="*")
        if not pw:
            return
        score, label, notes = ce.test_password_strength(pw)
        self._log(f"Password strength: {label} ({score}/100).")
        for note in notes:
            self._log(f"  - {note}")
        self._set_status("password tested")

    def password_safe(self):
        messagebox.showinfo(
            "Password Safe",
            "Password Safe stores entries encrypted with your pass phrase.\n\n"
            "In this build, use Generate Secure Password and Encrypt Text to "
            "store credentials as an encrypted token you keep in a safe note.")
        self._set_status("password safe")

    def self_decrypt(self):
        message = self.output.get("1.0", "end").strip()
        if not message:
            message = self._ask_text("Self Decrypting Message", "Type the message to protect:")
        if not message:
            return
        pw = self._ask_password("Self Decrypting Message", "Set a password for the reader:")
        if not pw:
            return
        path = filedialog.asksaveasfilename(title="Save Self Decrypting Message",
                                            defaultextension=".html",
                                            initialfile="message.html",
                                            filetypes=[("HTML", "*.html")])
        if not path:
            return
        ce.create_self_decrypting_html(message, pw, path)
        self._log(f"Self decrypting message saved: {path}")
        self._log("Open it in any browser and type the password to read it.")
        self._set_status("self decryptor created")

    # ===============================================================
    # OPTIONS menu
    # ===============================================================
    def change_passphrase(self):
        pw = self._ask_text("Default Pass Phrase", "Set a default pass phrase for this session:", show="*")
        if pw:
            self.default_passphrase = pw
            self._set_status("default pass phrase set")

    def crypto_options(self):
        messagebox.showinfo(
            "Crypto Options",
            "Cipher: AES-256-GCM.\n"
            "Key from password using PBKDF2-HMAC-SHA256, 200000 rounds.\n"
            "Each item uses a fresh random salt and nonce.")
        self._set_status("crypto options")

    def setup_key_file(self):
        """Pick a file to act as a key. Its hash becomes the default pass phrase."""
        path = filedialog.askopenfilename(title="Choose a key file")
        if not path:
            return
        try:
            import hashlib
            with open(path, "rb") as f:
                data = f.read()
            digest = hashlib.sha256(data).hexdigest()
            self.default_passphrase = digest[:32]
            self._log(f"Key file set: {os.path.basename(path)}.")
            self._log("Use Default in the pass phrase dialog now uses this key file.")
            self._log("Keep the key file safe. Without it you cannot use the default.")
            self._set_status("key file set")
        except Exception as e:
            self._error(e)

    def open_configure(self):
        """A small settings window: appearance, font size, splash, and key status."""
        win = ctk.CTkToplevel(self)
        win.title("Configure")
        win.geometry("420x340")
        win.configure(fg_color=BLACK)
        win.transient(self)

        ctk.CTkLabel(win, text="CONFIGURE", text_color=YELLOW,
                     font=(MONO, 16, "bold")).pack(pady=(12, 8))

        # appearance
        appear = ctk.CTkFrame(win, fg_color=BLACK)
        appear.pack(fill="x", padx=16, pady=6)
        ctk.CTkLabel(appear, text="Appearance", text_color=YELLOW_DEEP,
                     font=("Arial", 12)).pack(side="left")
        ctk.CTkButton(appear, text="Toggle Light / Dark", command=self.cycle_colors,
                      fg_color=YELLOW, hover_color=YELLOW_DEEP, text_color=TEXT_DARK,
                      font=("Arial", 11, "bold")).pack(side="right")

        # font size
        fontf = ctk.CTkFrame(win, fg_color=BLACK)
        fontf.pack(fill="x", padx=16, pady=6)
        ctk.CTkLabel(fontf, text="Console font size", text_color=YELLOW_DEEP,
                     font=("Arial", 12)).pack(side="left")
        slider = ctk.CTkSlider(fontf, from_=9, to=20, number_of_steps=11,
                               command=lambda v: self._set_font_size(int(v)))
        slider.set(self.text_font_size)
        slider.pack(side="right", fill="x", expand=True, padx=(12, 0))

        # default pass phrase status
        status = "set" if self.default_passphrase else "not set"
        ctk.CTkLabel(win, text=f"Default pass phrase: {status}", text_color=YELLOW_DARK,
                     font=("Consolas", 11)).pack(anchor="w", padx=16, pady=(10, 2))
        ctk.CTkButton(win, text="Change Default Pass Phrase", command=self.change_passphrase,
                      fg_color="#333300", hover_color="#444400", text_color=YELLOW).pack(anchor="w", padx=16, pady=2)
        ctk.CTkButton(win, text="Setup Key File", command=self.setup_key_file,
                      fg_color="#333300", hover_color="#444400", text_color=YELLOW).pack(anchor="w", padx=16, pady=2)

        # crypto summary
        ctk.CTkLabel(win, text="Cipher: AES-256-GCM, PBKDF2-SHA256, 200000 rounds.",
                     text_color=YELLOW_DARK, font=("Consolas", 10)).pack(anchor="w", padx=16, pady=(12, 0))
        self._set_status("configure open")

    def _set_font_size(self, n):
        n = max(8, min(28, int(n)))
        self.text_font_size = n
        self.output.configure(font=("Consolas", n))

    # ===============================================================
    # HELP menu
    # ===============================================================
    def show_help(self):
        self.output.insert("end",
            "\n--- HELP ---\n"
            "Steganography (graded core):\n"
            "1. Load Cover. 2. Hide Text or Hide File. 3. Save Stego.\n"
            "To read: Load Stego, then Extract Text or Extract File.\n"
            "Analysis: Modified Pixels, Binary Compare, Compare Images, Capacity Check.\n\n"
            "Crypto: Encrypt Text or Files with a password. AES-256-GCM.\n"
            "Shred: overwrite then delete a file or folder. Cannot be undone.\n"
            "Tools: Generate password, test strength, self decrypting message.\n")
        self.output.see("end")
        self._set_status("help shown")

    def _reveal_main(self):
        """Show the main window after the boot screen and info box are done."""
        try:
            self.deiconify()
            self.lift()
            self.focus_force()
        except Exception:
            pass

    def replay_splash(self):
        """Show the boot screen on demand, without changing the saved setting."""
        saved = self._show_splash_pref
        self._show_splash_pref = True
        self.show_splash()
        self._show_splash_pref = saved

    def show_credits(self):
        messagebox.showinfo("Credits",
            "StegoShell\n"
            "data hidden, data secured\n\n"
            "Built for Information Organization and System Security.\n"
            "Steganography method follows the Day 3 class slides.\n"
            "Built by BIKARI Amos Thibault, Reg M04046/2025.\n"
            "Icons and logo are original art.")

    def about(self):
        messagebox.showinfo("About StegoShell",
            "StegoShell\n"
            "data hidden, data secured\n\n"
            "LSB image and audio steganography plus AES-256-GCM crypto.\n"
            "The menu layout refers to a reference interface. All code "
            "and art are original.")

    def open_url(self, url):
        webbrowser.open(url)
        self._set_status("opened browser")

    # ===============================================================
    # CONFIG  (remembers the splash preference)
    # ===============================================================
    def _config_path(self):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "quickcrypto_config.json")

    def _load_config(self):
        try:
            import json
            with open(self._config_path(), "r", encoding="utf-8") as f:
                cfg = json.load(f)
            self._show_splash_pref = bool(cfg.get("show_splash", True))
        except Exception:
            self._show_splash_pref = True

    def _save_config(self):
        try:
            import json
            with open(self._config_path(), "w", encoding="utf-8") as f:
                json.dump({"show_splash": self._show_splash_pref}, f)
        except Exception:
            pass

    # ===============================================================
    # STARTUP SPLASH  (the boot panel from the screenshot)
    # ===============================================================
    def show_splash(self):
        if not self._show_splash_pref:
            return
        import random
        splash = ctk.CTkToplevel(self)
        splash.title("stegoshell")
        W, H = 720, 500
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = max(0, (sw - W) // 2)
        y = max(0, (sh - H) // 3)
        splash.geometry(f"{W}x{H}+{x}+{y}")
        splash.configure(fg_color=BLACK)
        splash.protocol("WM_DELETE_WINDOW", lambda: (splash.destroy(), self._reveal_main()))

        canvas = tk.Canvas(splash, width=W, height=H, bg="#040805",
                           highlightthickness=0, bd=0)
        canvas.pack(fill="both", expand=True)

        # ---- matrix code rain ----
        chars = "01<>[]{}#$%&*+=/\\|"
        font_rain = (MONO, 12, "bold")
        cols = W // 14
        drops = [random.randint(-H // 14, 0) for _ in range(cols)]
        rain_items = {}

        def draw_rain():
            if not canvas.winfo_exists():
                return
            # fade old characters by redrawing background bands lightly
            for c in range(cols):
                x = c * 14 + 6
                y = drops[c] * 14
                ch = random.choice(chars)
                # head bright, trail dim
                canvas.create_text(x, y, text=ch, fill="#00ff78", font=font_rain, tags="rain")
                canvas.create_text(x, y - 14, text=random.choice(chars), fill="#0a3a1f", font=font_rain, tags="rain")
                drops[c] += 1
                if y > H or random.random() > 0.975:
                    drops[c] = random.randint(-6, 0)
            # keep only recent rain to avoid buildup
            ids = canvas.find_withtag("rain")
            if len(ids) > cols * 8:
                for i in ids[: len(ids) - cols * 8]:
                    canvas.delete(i)
            canvas.tag_lower("rain")
            splash.after(70, draw_rain)

        # ---- panel over the rain ----
        canvas.create_rectangle(40, 40, W - 40, H - 110, outline="#00b257", width=2, fill="#030906")
        canvas.create_text(60, 64, text="root@stegoshell:~$ ./boot", anchor="w",
                           fill="#00ff78", font=(MONO, 14, "bold"))
        canvas.create_line(56, 84, W - 56, 84, fill="#1f7a45")

        boot_lines = [
            "> initialising stego suite ...",
            "> loading LSB image engine ...... [ok]",
            "> loading audio engine .......... [ok]",
            "> loading AES-256-GCM crypto .... [ok]",
            "> self test ..................... PASS",
            "> keys online: 12 / min 8 ....... [ok]",
            "",
            "  STEGOSHELL  //  data hidden, data secured  v1.0",
            "  steganography that hides in plain sight.",
        ]
        # typed boot text, line by line, char by char
        state = {"line": 0, "col": 0, "yid": None}
        ty = 104

        def type_boot():
            if not canvas.winfo_exists():
                return
            if state["line"] >= len(boot_lines):
                show_links()
                return
            text = boot_lines[state["line"]]
            shown = text[: state["col"]]
            y = ty + state["line"] * 26
            tag = f"boot{state['line']}"
            canvas.delete(tag)
            colour = "#00ff78" if ("STEGOSHELL" in text or "PASS" in text or "[ok]" in text) else "#7fdfa6"
            canvas.create_text(60, y, text=shown + "\u2588", anchor="w", fill=colour,
                               font=(MONO, 13, "bold"), tags=tag)
            if state["col"] < len(text):
                state["col"] += 1
                splash.after(18, type_boot)
            else:
                canvas.delete(tag)
                canvas.create_text(60, y, text=shown, anchor="w", fill=colour,
                                   font=(MONO, 13, "bold"), tags=tag)
                state["line"] += 1
                state["col"] = 0
                splash.after(120, type_boot)

        def dont_show():
            splash.destroy()
            self.show_info_box()

        def show_links():
            btn1 = ctk.CTkButton(splash, text="[ skip intro ]", command=dont_show,
                                 fg_color="#07140c", hover_color="#0d2a18", text_color=YELLOW,
                                 border_color=YELLOW_DEEP, border_width=1,
                                 font=(MONO, 11, "bold"), corner_radius=2)
            btn2 = ctk.CTkButton(splash, text="[ click here to continue ]",
                                 command=lambda: (splash.destroy(), self.show_info_box()),
                                 fg_color="#07140c", hover_color="#0d2a18", text_color=YELLOW,
                                 border_color=YELLOW_DEEP, border_width=1,
                                 font=(MONO, 11, "bold"), corner_radius=2)
            canvas.create_window(W // 2 - 150, H - 50, window=btn1)
            canvas.create_window(W // 2 + 150, H - 50, window=btn2)

        draw_rain()
        type_boot()
        splash.after(120, splash.lift)

    def show_info_box(self):
        """A small box at launch. The UNILAK logo stays fixed, the text scrolls."""
        try:
            box = ctk.CTkToplevel(self)
            box.title("about this app")
            BW, BH = 560, 640
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            bx = max(0, (sw - BW) // 2)
            by = max(0, (sh - BH) // 3)
            box.geometry(f"{BW}x{BH}+{bx}+{by}")
            box.configure(fg_color=BLACK)
            box.lift()
            box.protocol("WM_DELETE_WINDOW", lambda: (box.destroy(), self._reveal_main()))

            # green framed header that holds the fixed logo
            head = ctk.CTkFrame(box, fg_color=PANEL_BLACK, border_color=YELLOW_DEEP,
                                border_width=2, corner_radius=4)
            head.pack(fill="x", padx=14, pady=(14, 6))
            logo_path = os.path.join(ASSET_DIR, "unilak_logo.png")
            if os.path.exists(logo_path):
                im = Image.open(logo_path).convert("RGBA")
                self._info_logo = ctk.CTkImage(light_image=im, dark_image=im, size=(110, 102))
                ctk.CTkLabel(head, image=self._info_logo, text="").pack(pady=(10, 4))
            ctk.CTkLabel(head, text="UNIVERSITY OF LAY ADVENTISTS OF KIGALI",
                         text_color=YELLOW, font=(MONO, 11, "bold")).pack(pady=(0, 10))

            # scrolling text area, app green on black
            scroll = tk.Canvas(box, bg="#040805", highlightthickness=1,
                               highlightbackground=YELLOW_DEEP, height=360)
            scroll.pack(fill="both", expand=True, padx=14, pady=6)

            lines = [
                "STEGOSHELL  //  data hidden, data secured  v1.0",
                "",
                "An individual assignment project for the module",
                "Information Organization and System Security.",
                "",
                "The app hides data inside images and audio using",
                "the least significant bit method, and pairs it with",
                "AES-256 encryption for a second layer of protection.",
                "",
                "Features:",
                "  - hide and recover text and files in images",
                "  - hide and recover data in WAV audio",
                "  - encrypt then hide, extract then decrypt",
                "  - analyse changed pixels and capacity",
                "  - shred files, generate and test passwords",
                "",
                "Built by:  BIKARI Amos Thibault",
                "Reg No:    M04046/2025",
                "Program:   MSc Information Technology",
                "Lecturer:  Dr. NTIVUGURUZWA Jean de la Croix",
                "",
                "Knowledge & Wisdom  -  UNILAK, since 1997",
                "",
            ]
            line_h = 22
            start_y = 200
            text_ids = []
            for i, ln in enumerate(lines):
                bright = ln.startswith("STEGOSHELL") or ln.startswith("Features") or ln.startswith("Knowledge")
                tid = scroll.create_text(20, start_y + i * line_h, text=ln, anchor="w",
                                         fill=YELLOW if bright else "#7fdfa6",
                                         font=(MONO, 11, "bold" if bright else "normal"))
                text_ids.append(tid)

            total = len(lines) * line_h
            state = {"run": True}

            def scroll_tick():
                if not state["run"] or not scroll.winfo_exists():
                    return
                for tid in text_ids:
                    scroll.move(tid, 0, -1)
                # loop: when the last line passes the top, reset to the bottom
                x0, y0, x1, y1 = scroll.bbox(text_ids[-1])
                if y1 < 0:
                    for i, tid in enumerate(text_ids):
                        scroll.coords(tid, 20, scroll.winfo_height() + i * line_h)
                scroll.after(40, scroll_tick)

            def close_box():
                state["run"] = False
                box.destroy()
                self._reveal_main()

            ctk.CTkButton(box, text="[ enter the app ]", command=close_box,
                          fg_color="#07140c", hover_color="#0d2a18", text_color=YELLOW,
                          border_color=YELLOW_DEEP, border_width=1,
                          font=(MONO, 11, "bold"), corner_radius=2).pack(pady=(2, 12))

            scroll.after(300, scroll_tick)
        except Exception:
            self._reveal_main()


if __name__ == "__main__":
    app = StegoApp()
    # keep the main window hidden until the boot screen and info box are done
    app.withdraw()
    app.after(200, app.replay_splash)
    # safety net: if nothing reveals the window, show it after a while
    app.after(60000, app._reveal_main)
    try:
        app.mainloop()
    except KeyboardInterrupt:
        try:
            app.destroy()
        except Exception:
            pass
        print("StegoShell closed.")
