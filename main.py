"""
YTSaver Pro - Full Featured Video Downloader
- YouTube: video, shorts, playlist, channel
- Instagram: post, reel, profile (private with login)
- TikTok: video, account (private with login)
- Facebook: video, reel, page (private with login)
- Account login manager (no password stored, uses session cookies)
- Custom folder names
- Android 5.0+ compatible
"""

import os
import json
import threading
import re
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.progressbar import ProgressBar
from kivy.uix.popup import Popup
from kivy.uix.switch import Switch
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.utils import get_color_from_hex
from kivy.graphics import Color, RoundedRectangle
import yt_dlp

# ── Colors ────────────────────────────────────────────────
BG_DARK  = get_color_from_hex("#0D0D0D")
BG_CARD  = get_color_from_hex("#1A1A2E")
BG_INPUT = get_color_from_hex("#16213E")
ACCENT   = get_color_from_hex("#E94560")
ACCENT2  = get_color_from_hex("#0F3460")
ACCENT3  = get_color_from_hex("#533483")
GREEN    = get_color_from_hex("#4CAF50")
ORANGE   = get_color_from_hex("#FF9800")
YELLOW   = get_color_from_hex("#FFD700")
TEXT_W   = get_color_from_hex("#FFFFFF")
TEXT_G   = get_color_from_hex("#999999")

Window.clearcolor = BG_DARK

# ── Storage path ──────────────────────────────────────────
def get_base_path():
    try:
        from android.storage import primary_external_storage_path
        base = os.path.join(primary_external_storage_path(), "Download", "YTSaver")
    except ImportError:
        base = os.path.join(os.path.expanduser("~"), "Downloads", "YTSaver")
    os.makedirs(base, exist_ok=True)
    return base

def get_cookies_dir():
    path = os.path.join(get_base_path(), "cookies")
    os.makedirs(path, exist_ok=True)
    return path

def get_sessions_file():
    return os.path.join(get_base_path(), "sessions.json")

# ── Session manager ───────────────────────────────────────
class SessionManager:
    """Stores which platforms are logged in (via cookie files)"""
    def __init__(self):
        self._file = get_sessions_file()
        self._data = self._load()

    def _load(self):
        try:
            with open(self._file) as f:
                return json.load(f)
        except:
            return {}

    def _save(self):
        try:
            with open(self._file, 'w') as f:
                json.dump(self._data, f)
        except:
            pass

    def is_logged_in(self, platform):
        cookie_path = os.path.join(get_cookies_dir(), f"{platform}.txt")
        return os.path.exists(cookie_path) and os.path.getsize(cookie_path) > 100

    def get_cookie_path(self, platform):
        p = os.path.join(get_cookies_dir(), f"{platform}.txt")
        return p if os.path.exists(p) else None

    def save_cookies_text(self, platform, cookies_text):
        path = os.path.join(get_cookies_dir(), f"{platform}.txt")
        with open(path, 'w') as f:
            f.write(cookies_text.strip())
        self._data[platform] = True
        self._save()
        return path

    def logout(self, platform):
        path = os.path.join(get_cookies_dir(), f"{platform}.txt")
        if os.path.exists(path):
            os.remove(path)
        self._data.pop(platform, None)
        self._save()

SESSION = SessionManager()

# ── URL type detector ─────────────────────────────────────
def detect_url(url):
    u = url.lower().strip()

    # YouTube Shorts
    if "youtube.com/shorts" in u:
        return "yt_short", "▶ YouTube Short"
    # YouTube Playlist
    if "youtube.com/playlist" in u or ("youtube.com" in u and "list=" in u):
        return "yt_playlist", "🎵 YouTube Playlist"
    # YouTube Channel
    if re.search(r'youtube\.com/(@|c/|channel/|user/)', u):
        return "yt_channel", "📺 YouTube Channel"
    # YouTube single
    if "youtu.be" in u or "youtube.com/watch" in u:
        return "yt_single", "▶ YouTube Video"

    # Instagram profile
    if "instagram.com" in u and re.search(r'instagram\.com/[^/]+/?$', u.rstrip('/')):
        return "insta_profile", "📸 Instagram Profile"
    # Instagram post/reel
    if "instagram.com" in u and ("/p/" in u or "/reel/" in u or "/tv/" in u):
        return "insta_single", "📸 Instagram Post/Reel"

    # TikTok account
    if "tiktok.com" in u and re.search(r'tiktok\.com/@[^/]+/?$', u.rstrip('/')):
        return "tiktok_account", "🎵 TikTok Account"
    # TikTok video
    if "tiktok.com" in u:
        return "tiktok_single", "🎵 TikTok Video"

    # Facebook reels
    if ("facebook.com" in u or "fb.com" in u) and "/reel" in u:
        return "fb_reel", "🎬 Facebook Reel"
    # Facebook page
    if ("facebook.com" in u or "fb.com" in u) and re.search(r'facebook\.com/[^/]+/?$', u.rstrip('/')):
        return "fb_page", "👥 Facebook Page"
    # Facebook video
    if "facebook.com" in u or "fb.com" in u or "fb.watch" in u:
        return "fb_single", "👥 Facebook Video"

    # Twitter/X
    if "twitter.com" in u or "x.com" in u:
        return "tw_single", "🐦 Twitter/X Video"

    # Dailymotion
    if "dailymotion.com" in u:
        return "dm_single", "▶ Dailymotion"

    return "unknown", "🌐 Video"

BULK_TYPES = {"yt_playlist", "yt_channel", "insta_profile", "tiktok_account", "fb_page"}
PLATFORM_MAP = {
    "yt_single": "youtube", "yt_short": "youtube", "yt_playlist": "youtube", "yt_channel": "youtube",
    "insta_single": "instagram", "insta_profile": "instagram",
    "tiktok_single": "tiktok", "tiktok_account": "tiktok",
    "fb_single": "facebook", "fb_reel": "facebook", "fb_page": "facebook",
    "tw_single": "twitter",
}

# ── Reusable card widget ───────────────────────────────────
class DLCard(BoxLayout):
    def __init__(self, title, url_type="", **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.size_hint_y = None
        self.height = dp(96)
        self.padding = [dp(12), dp(8)]
        self.spacing = dp(3)
        with self.canvas.before:
            Color(*BG_CARD)
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(8)])
        self.bind(pos=lambda o,v: setattr(self._bg,'pos',v),
                  size=lambda o,v: setattr(self._bg,'size',v))

        badge_color = {
            "yt_single":"#FF0000","yt_short":"#FF4444","yt_playlist":"#FF0000","yt_channel":"#FF0000",
            "insta_single":"#C13584","insta_profile":"#C13584",
            "tiktok_single":"#69C9D0","tiktok_account":"#69C9D0",
            "fb_single":"#1877F2","fb_reel":"#1877F2","fb_page":"#1877F2",
        }.get(url_type, "#888888")

        top = BoxLayout(size_hint_y=None, height=dp(22), spacing=dp(4))
        top.add_widget(Label(text=f"[color={badge_color}]●[/color]",
            markup=True, font_size=dp(10), size_hint_x=None, width=dp(14)))
        self.title_lbl = Label(text=title[:58]+("..." if len(title)>58 else ""),
            font_size=dp(13), color=TEXT_W, halign="left",
            text_size=(Window.width-dp(60), None))
        top.add_widget(self.title_lbl)
        self.add_widget(top)

        self.bar = ProgressBar(max=100, value=0, size_hint_y=None, height=dp(6))
        self.add_widget(self.bar)

        bot = BoxLayout(size_hint_y=None, height=dp(20))
        self.status_lbl = Label(text="Tayari...", font_size=dp(11), color=TEXT_G,
            halign="left", size_hint_x=0.72,
            text_size=(Window.width*0.68, None))
        self.count_lbl = Label(text="", font_size=dp(11), color=YELLOW,
            halign="right", size_hint_x=0.28)
        bot.add_widget(self.status_lbl)
        bot.add_widget(self.count_lbl)
        self.add_widget(bot)

    def update(self, status, pct=None, count=""):
        if pct is not None:
            self.bar.value = max(0, min(100, pct))
        self.status_lbl.text = status
        self.count_lbl.text = count


# ── Login Popup ───────────────────────────────────────────
class LoginPopup(Popup):
    """Paste cookies.txt content to login"""
    PLATFORMS = {
        "youtube":   ("YouTube",   "#FF0000"),
        "instagram": ("Instagram", "#C13584"),
        "tiktok":    ("TikTok",    "#69C9D0"),
        "facebook":  ("Facebook",  "#1877F2"),
    }

    def __init__(self, on_done=None, **kwargs):
        super().__init__(**kwargs)
        self.title = "Account Login"
        self.size_hint = (0.95, 0.88)
        self.background_color = BG_CARD
        self.title_color = ACCENT
        self._on_done = on_done

        root = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))

        # Instructions
        instr = Label(
            text=(
                "[b]Kaise login karein?[/b]\n"
                "1. PC par Chrome mein platform par login karein\n"
                "2. Extension install karein: [color=#FFD700]'Get cookies.txt LOCALLY'[/color]\n"
                "3. Wahan se cookies.txt copy karein\n"
                "4. Neeche paste karein → Save"
            ),
            markup=True, font_size=dp(12), color=TEXT_G,
            size_hint_y=None, height=dp(88),
            halign="left", valign="top",
            text_size=(Window.width*0.88, None)
        )
        root.add_widget(instr)

        # Platform selector
        plat_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
        plat_row.add_widget(Label(text="Platform:", font_size=dp(13), color=TEXT_G,
            size_hint_x=None, width=dp(72)))
        self.plat_spinner = Spinner(
            text="instagram",
            values=["youtube", "instagram", "tiktok", "facebook"],
            background_color=ACCENT2, color=TEXT_W, font_size=dp(13)
        )
        self.plat_spinner.bind(text=self._update_status)
        plat_row.add_widget(self.plat_spinner)
        root.add_widget(plat_row)

        # Status row
        self.status_row = BoxLayout(size_hint_y=None, height=dp(28), spacing=dp(8))
        self.login_status = Label(text="", font_size=dp(12), color=TEXT_G, halign="left")
        self.logout_btn = Button(text="Logout", font_size=dp(11),
            size_hint_x=None, width=dp(70), background_color=ACCENT)
        self.logout_btn.bind(on_press=self._do_logout)
        self.status_row.add_widget(self.login_status)
        self.status_row.add_widget(self.logout_btn)
        root.add_widget(self.status_row)

        # Cookies text area
        root.add_widget(Label(text="Cookies.txt content yahan paste karein:",
            font_size=dp(12), color=TEXT_G,
            size_hint_y=None, height=dp(22), halign="left",
            text_size=(Window.width*0.88, None)))

        self.cookie_input = TextInput(
            hint_text="# Netscape HTTP Cookie File\n.youtube.com\tTRUE\t/\t...",
            multiline=True,
            background_color=BG_INPUT,
            foreground_color=TEXT_W,
            hint_text_color=TEXT_G,
            font_size=dp(11),
            size_hint_y=0.42
        )
        root.add_widget(self.cookie_input)

        # Buttons
        btn_row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(10))
        cancel = Button(text="Band Karo", background_color=ACCENT2, color=TEXT_W, font_size=dp(13))
        cancel.bind(on_press=self.dismiss)
        save = Button(text="💾 Save & Login", background_color=ACCENT, color=TEXT_W, font_size=dp(13))
        save.bind(on_press=self._save_cookies)
        btn_row.add_widget(cancel)
        btn_row.add_widget(save)
        root.add_widget(btn_row)

        self.content = root
        self._update_status(None, "instagram")

    def _update_status(self, obj, platform):
        logged = SESSION.is_logged_in(platform)
        if logged:
            self.login_status.text = f"✅ {platform} — Login hai"
            self.login_status.color = GREEN
            self.logout_btn.opacity = 1
            self.logout_btn.disabled = False
        else:
            self.login_status.text = f"❌ {platform} — Login nahi"
            self.login_status.color = ORANGE
            self.logout_btn.opacity = 0.3
            self.logout_btn.disabled = True

    def _do_logout(self, *a):
        platform = self.plat_spinner.text
        SESSION.logout(platform)
        self._update_status(None, platform)
        self.cookie_input.text = ""

    def _save_cookies(self, *a):
        platform = self.plat_spinner.text
        text = self.cookie_input.text.strip()
        if not text or len(text) < 50:
            self.login_status.text = "❌ Cookies bahut choti hain!"
            self.login_status.color = ORANGE
            return
        SESSION.save_cookies_text(platform, text)
        self._update_status(None, platform)
        self.cookie_input.text = ""
        if self._on_done:
            self._on_done()


# ── Bulk Options Popup ────────────────────────────────────
class BulkPopup(Popup):
    def __init__(self, label, url_type, on_confirm, **kwargs):
        super().__init__(**kwargs)
        self.title = "Bulk Download Settings"
        self.size_hint = (0.93, None)
        self.height = dp(370)
        self.background_color = BG_CARD
        self.title_color = ACCENT
        self._on_confirm = on_confirm

        root = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(14))

        # Detected type
        root.add_widget(Label(
            text=f"Detected: [color=#E94560]{label}[/color]",
            markup=True, font_size=dp(13), color=TEXT_W,
            size_hint_y=None, height=dp(26)
        ))

        def row(lbl_text, widget):
            r = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
            r.add_widget(Label(text=lbl_text, font_size=dp(13), color=TEXT_G,
                size_hint_x=0.38))
            r.add_widget(widget)
            root.add_widget(r)

        # Max videos
        self.max_sp = Spinner(text="Sab (Unlimited)",
            values=["Sab (Unlimited)","5","10","20","50","100","200"],
            background_color=ACCENT2, color=TEXT_W, font_size=dp(12))
        row("Max Videos:", self.max_sp)

        # Quality
        self.q_sp = Spinner(text="720p",
            values=["4K (2160p)","1080p","720p","480p","360p","240p","Audio MP3"],
            background_color=ACCENT2, color=TEXT_W, font_size=dp(12))
        row("Quality:", self.q_sp)

        # Format
        self.f_sp = Spinner(text="MP4",
            values=["MP4","MKV","MP3","M4A"],
            background_color=ACCENT2, color=TEXT_W, font_size=dp(12))
        row("Format:", self.f_sp)

        # Custom folder
        self.folder_inp = TextInput(
            hint_text="Custom folder (khali = auto channel/page naam)",
            multiline=False, size_hint_y=None, height=dp(42),
            background_color=BG_INPUT, foreground_color=TEXT_W,
            hint_text_color=TEXT_G, font_size=dp(12), padding=[dp(8),dp(10)]
        )
        root.add_widget(self.folder_inp)

        # Include Reels toggle (for FB/Insta)
        if url_type in ("fb_page", "insta_profile"):
            reels_row = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(8))
            reels_row.add_widget(Label(text="Reels bhi shaamil karein:",
                font_size=dp(13), color=TEXT_G, size_hint_x=0.72))
            self.reels_sw = Switch(active=True, size_hint_x=0.28)
            reels_row.add_widget(self.reels_sw)
            root.add_widget(reels_row)
        else:
            self.reels_sw = None

        # Buttons
        btn_row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(10))
        Button(text="Ruk Jao", background_color=ACCENT2, color=TEXT_W,
               font_size=dp(13)).bind(on_press=self.dismiss)
        b_cancel = Button(text="Ruk Jao", background_color=ACCENT2, color=TEXT_W, font_size=dp(13))
        b_cancel.bind(on_press=self.dismiss)
        b_go = Button(text="⬇ Shuru Karo", background_color=ACCENT, color=TEXT_W, font_size=dp(13))
        b_go.bind(on_press=self._go)
        btn_row.add_widget(b_cancel)
        btn_row.add_widget(b_go)
        root.add_widget(btn_row)
        self.content = root

    def _go(self, *a):
        max_v = self.max_sp.text
        self._on_confirm(
            max_count=None if "Sab" in max_v else int(max_v),
            quality=self.q_sp.text,
            fmt=self.f_sp.text,
            folder=self.folder_inp.text.strip(),
            include_reels=self.reels_sw.active if self.reels_sw else False
        )
        self.dismiss()


# ── Accounts Status Bar ───────────────────────────────────
class AccountsBar(BoxLayout):
    PLATFORMS = [
        ("YT",   "youtube",   "#FF0000"),
        ("IG",   "instagram", "#C13584"),
        ("TT",   "tiktok",    "#69C9D0"),
        ("FB",   "facebook",  "#1877F2"),
    ]

    def __init__(self, on_manage, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.size_hint_y = None
        self.height = dp(34)
        self.spacing = dp(4)
        self._on_manage = on_manage
        self._badges = {}
        self._build()

    def _build(self):
        self.add_widget(Label(text="Accounts:", font_size=dp(11), color=TEXT_G,
            size_hint_x=None, width=dp(64)))
        for short, plat, color in self.PLATFORMS:
            logged = SESSION.is_logged_in(plat)
            lbl = Label(
                text=f"[color={'#4CAF50' if logged else '#555'}]{'✔' if logged else '✘'} {short}[/color]",
                markup=True, font_size=dp(11), size_hint_x=0.2
            )
            self._badges[plat] = lbl
            self.add_widget(lbl)

        manage_btn = Button(text="⚙ Manage", font_size=dp(11),
            background_color=ACCENT2, color=TEXT_W,
            size_hint_x=None, width=dp(72))
        manage_btn.bind(on_press=lambda *a: self._on_manage())
        self.add_widget(manage_btn)

    def refresh(self):
        for plat, lbl in self._badges.items():
            logged = SESSION.is_logged_in(plat)
            lbl.text = (
                f"[color={'#4CAF50' if logged else '#555'}]"
                f"{'✔' if logged else '✘'} "
                f"{next(s for s,p,c in self.PLATFORMS if p==plat)}"
                f"[/color]"
            )


# ── Main Screen ───────────────────────────────────────────
class MainScreen(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.spacing = dp(6)
        self.padding = [dp(10), dp(12), dp(10), dp(8)]
        self._dl_items = {}
        self._cur_type = "unknown"
        self._build()

    def _build(self):
        # Header
        hdr = BoxLayout(size_hint_y=None, height=dp(40))
        hdr.add_widget(Label(
            text="[b]YT[/b][color=#E94560]Saver[/color] [size=10][color=#888]Pro[/color][/size]",
            markup=True, font_size=dp(22), color=TEXT_W, halign="left", size_hint_x=0.5))
        hdr.add_widget(Label(
            text="YT • IG • TT • FB • Twitter",
            font_size=dp(10), color=TEXT_G, halign="right", size_hint_x=0.5))
        self.add_widget(hdr)

        # Accounts bar
        self.acc_bar = AccountsBar(on_manage=self._open_login)
        self.add_widget(self.acc_bar)

        # URL Card
        url_card = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(116),
            spacing=dp(5), padding=[dp(12), dp(8)])
        with url_card.canvas.before:
            Color(*BG_CARD)
            self._uc = RoundedRectangle(pos=url_card.pos, size=url_card.size, radius=[dp(10)])
        url_card.bind(pos=lambda o,v: setattr(self._uc,'pos',v),
                      size=lambda o,v: setattr(self._uc,'size',v))

        self.detect_lbl = Label(
            text="🔗 Link paste karein",
            font_size=dp(11), color=TEXT_G,
            size_hint_y=None, height=dp(18), halign="left",
            text_size=(Window.width-dp(28), None))
        url_card.add_widget(self.detect_lbl)

        self.url_inp = TextInput(
            hint_text="https://youtube.com / instagram.com / tiktok.com / facebook.com ...",
            multiline=False, size_hint_y=None, height=dp(44),
            background_color=BG_INPUT, foreground_color=TEXT_W,
            cursor_color=ACCENT, hint_text_color=TEXT_G,
            font_size=dp(13), padding=[dp(10), dp(12)])
        self.url_inp.bind(text=self._on_url)
        url_card.add_widget(self.url_inp)

        self.type_lbl = Label(text="", font_size=dp(12), color=ACCENT,
            size_hint_y=None, height=dp(18), halign="left",
            text_size=(Window.width-dp(28), None))
        url_card.add_widget(self.type_lbl)
        self.add_widget(url_card)

        # Single video options
        opt = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
        opt.add_widget(Label(text="Quality:", font_size=dp(11), color=TEXT_G,
            size_hint_x=None, width=dp(48)))
        self.q_sp = Spinner(text="1080p",
            values=["4K (2160p)","1080p","720p","480p","360p","240p","Audio MP3"],
            size_hint_x=0.46, background_color=ACCENT2, color=TEXT_W, font_size=dp(11))
        opt.add_widget(self.q_sp)
        opt.add_widget(Label(text="Format:", font_size=dp(11), color=TEXT_G,
            size_hint_x=None, width=dp(46)))
        self.f_sp = Spinner(text="MP4",
            values=["MP4","MKV","WEBM","MP3","M4A"],
            size_hint_x=0.36, background_color=ACCENT2, color=TEXT_W, font_size=dp(11))
        opt.add_widget(self.f_sp)
        self.add_widget(opt)

        # Download button
        self.dl_btn = Button(text="⬇  DOWNLOAD KAREIN",
            size_hint_y=None, height=dp(50),
            background_color=ACCENT, color=TEXT_W, font_size=dp(14), bold=True)
        self.dl_btn.bind(on_press=self._on_dl_press)
        self.add_widget(self.dl_btn)

        # Downloads header
        dh = BoxLayout(size_hint_y=None, height=dp(26), spacing=dp(6))
        dh.add_widget(Label(text="Downloads", font_size=dp(12), color=TEXT_G,
            halign="left", size_hint_x=0.55,
            text_size=(Window.width*0.55, None)))
        dh.add_widget(Label(size_hint_x=0.2))
        clr = Button(text="🗑 Saaf", font_size=dp(11), background_color=BG_CARD,
            color=TEXT_G, size_hint_x=0.25)
        clr.bind(on_press=lambda *a: (self._dl_layout.clear_widgets(), self._dl_items.clear()))
        dh.add_widget(clr)
        self.add_widget(dh)

        scroll = ScrollView()
        self._dl_layout = GridLayout(cols=1, spacing=dp(5),
            size_hint_y=None, padding=[0, dp(2)])
        self._dl_layout.bind(minimum_height=self._dl_layout.setter('height'))
        scroll.add_widget(self._dl_layout)
        self.add_widget(scroll)

    # ── URL change ────────────────────────────────────────
    def _on_url(self, obj, val):
        url = val.strip()
        if url.startswith("http"):
            t, label = detect_url(url)
            self._cur_type = t
            self.type_lbl.text = label
            platform = PLATFORM_MAP.get(t, "")
            logged = SESSION.is_logged_in(platform) if platform else False
            if t in BULK_TYPES:
                self.dl_btn.text = "⬇  BULK DOWNLOAD KAREIN"
                self.dl_btn.background_color = ACCENT3
            else:
                self.dl_btn.text = "⬇  DOWNLOAD KAREIN"
                self.dl_btn.background_color = ACCENT
            # Login hint
            if platform and not logged and t in BULK_TYPES:
                self.detect_lbl.text = f"⚠ {platform.title()} login nahi — private content nahi chalega"
                self.detect_lbl.color = ORANGE
            else:
                self.detect_lbl.text = "🔗 Link paste karein"
                self.detect_lbl.color = TEXT_G
        else:
            self.type_lbl.text = ""
            self.detect_lbl.text = "🔗 Link paste karein"
            self.detect_lbl.color = TEXT_G
            self.dl_btn.text = "⬇  DOWNLOAD KAREIN"
            self.dl_btn.background_color = ACCENT

    # ── Download button ───────────────────────────────────
    def _on_dl_press(self, *a):
        url = self.url_inp.text.strip()
        if not url.startswith("http"):
            self._popup("Galti!", "Sahih link paste karein.")
            return
        t, label = detect_url(url)
        if t in BULK_TYPES:
            BulkPopup(label=label, url_type=t,
                on_confirm=lambda **kw: self._start_bulk(url, t, label, **kw)
            ).open()
        else:
            self._start_single(url, t)
        self.url_inp.text = ""

    # ── Single download ───────────────────────────────────
    def _start_single(self, url, url_type):
        fmt, ext = self._qf(self.q_sp.text, self.f_sp.text)
        card = DLCard("Checking...", url_type)
        self._dl_layout.add_widget(card)
        did = id(card); self._dl_items[did] = card
        self.dl_btn.disabled = True
        threading.Thread(target=self._do_single,
            args=(url, url_type, fmt, ext, did), daemon=True).start()

    def _do_single(self, url, url_type, fmt, ext, did):
        path = get_base_path()
        platform = PLATFORM_MAP.get(url_type, "")
        cookie = SESSION.get_cookie_path(platform)

        def hook(d):
            card = self._dl_items.get(did)
            if not card: return
            if d['status'] == 'downloading':
                tb = d.get('total_bytes') or d.get('total_bytes_estimate', 1)
                db = d.get('downloaded_bytes', 0)
                pct = int(db/tb*100) if tb else 0
                spd = d.get('speed', 0) or 0
                ss = f"{spd/1024:.0f}KB/s" if spd < 1048576 else f"{spd/1048576:.1f}MB/s"
                title = d.get('info_dict',{}).get('title','Video')[:50]
                Clock.schedule_once(lambda dt: (
                    setattr(card.title_lbl,'text', title),
                    card.update(f"⬇ {pct}% • {ss}", pct)
                ))
            elif d['status'] == 'finished':
                Clock.schedule_once(lambda dt: card.update("✅ Saving...", 100))

        opts = {
            'format': fmt,
            'outtmpl': os.path.join(path, '%(title)s.%(ext)s'),
            'progress_hooks': [hook],
            'merge_output_format': ext if ext not in ('mp3','m4a') else None,
            'postprocessors': [],
            'quiet': True, 'no_warnings': True, 'socket_timeout': 30,
        }
        if cookie:
            opts['cookiefile'] = cookie
        if ext in ('mp3','m4a'):
            opts['postprocessors'].append({
                'key': 'FFmpegExtractAudio',
                'preferredcodec': ext, 'preferredquality': '192'
            })
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get('title','Video')
                card = self._dl_items.get(did)
                if card:
                    Clock.schedule_once(lambda dt: (
                        setattr(card.title_lbl,'text', title[:58]),
                        card.update("✅ Mukammal!", 100),
                        setattr(card.status_lbl,'color', GREEN)
                    ))
        except Exception as e:
            card = self._dl_items.get(did)
            if card:
                Clock.schedule_once(lambda dt: (
                    card.update(f"❌ {str(e)[:65]}", 0),
                    setattr(card.status_lbl,'color', ORANGE)
                ))
        finally:
            Clock.schedule_once(lambda dt: self._re_enable())

    # ── Bulk download ─────────────────────────────────────
    def _start_bulk(self, url, url_type, label, max_count, quality, fmt, folder, include_reels):
        card = DLCard(f"{label}", url_type)
        self._dl_layout.add_widget(card)
        did = id(card); self._dl_items[did] = card
        self.dl_btn.disabled = True
        threading.Thread(target=self._do_bulk,
            args=(url, url_type, label, max_count, quality, fmt, folder, include_reels, did),
            daemon=True).start()

    def _do_bulk(self, url, url_type, label, max_count, quality, fmt, folder, include_reels, did):
        base = get_base_path()
        platform = PLATFORM_MAP.get(url_type, "")
        cookie = SESSION.get_cookie_path(platform)
        fmt_str, ext = self._qf(quality, fmt)

        done = [0]
        total = [0]

        def hook(d):
            card = self._dl_items.get(did)
            if not card: return
            if d['status'] == 'downloading':
                tb = d.get('total_bytes') or d.get('total_bytes_estimate', 1)
                db = d.get('downloaded_bytes', 0)
                pct = int(db/tb*100) if tb else 0
                spd = d.get('speed',0) or 0
                ss = f"{spd/1024:.0f}KB/s" if spd < 1048576 else f"{spd/1048576:.1f}MB/s"
                title = d.get('info_dict',{}).get('title','')[:40]
                cnt = f"{done[0]}/{total[0]}" if total[0] else f"{done[0]}"
                Clock.schedule_once(lambda dt: (
                    setattr(card.title_lbl,'text', title or label),
                    card.update(f"⬇ {pct}% • {ss}", pct, cnt)
                ))
            elif d['status'] == 'finished':
                done[0] += 1
                cnt = f"{done[0]}/{total[0]}" if total[0] else f"{done[0]}"
                Clock.schedule_once(lambda dt: card.update(f"✅ Video {done[0]} save", 100, cnt))

        # Folder name logic:
        # Custom > channel/page name > default
        if folder:
            out_folder = folder
        else:
            # Auto: will use uploader name from metadata
            out_folder = "%(uploader)s"

        opts = {
            'format': fmt_str,
            'outtmpl': os.path.join(base, out_folder, '%(title)s.%(ext)s'),
            'progress_hooks': [hook],
            'merge_output_format': ext if ext not in ('mp3','m4a') else None,
            'postprocessors': [],
            'ignoreerrors': True,
            'quiet': True, 'no_warnings': True, 'socket_timeout': 30,
        }
        if cookie:
            opts['cookiefile'] = cookie
        if max_count:
            opts['playlistend'] = max_count
        if ext in ('mp3','m4a'):
            opts['postprocessors'].append({
                'key': 'FFmpegExtractAudio',
                'preferredcodec': ext, 'preferredquality': '192'
            })

        # Platform tweaks
        actual_url = url
        if url_type == "yt_channel":
            # Force /videos tab
            clean = url.rstrip('/')
            if not clean.endswith('/videos'):
                clean += '/videos'
            actual_url = clean

        if url_type == "fb_page" and include_reels:
            # yt-dlp will get both videos and reels from page URL
            pass

        if url_type == "insta_profile" and include_reels:
            # yt-dlp handles both posts and reels from profile
            pass

        card = self._dl_items.get(did)
        Clock.schedule_once(lambda dt: card.update("📋 List ban rahi hai...", 5))

        try:
            # Pre-fetch count
            flat_opts = dict(opts)
            flat_opts['extract_flat'] = 'in_playlist'
            flat_opts['quiet'] = True
            try:
                with yt_dlp.YoutubeDL(flat_opts) as ydl_f:
                    pre = ydl_f.extract_info(actual_url, download=False)
                    entries = pre.get('entries', []) or []
                    total[0] = min(len(entries), max_count) if max_count else len(entries)
                    Clock.schedule_once(lambda dt: card.update(
                        f"📋 {total[0]} videos mili, shuru karte hain...", 10,
                        f"0/{total[0]}"))
            except:
                pass

            # Actual download
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([actual_url])

            card = self._dl_items.get(did)
            fc = done[0]
            if card:
                Clock.schedule_once(lambda dt: (
                    setattr(card.title_lbl,'text', label),
                    card.update(f"✅ {fc} videos mukammal!", 100, f"{fc} done"),
                    setattr(card.status_lbl,'color', GREEN)
                ))
        except Exception as e:
            card = self._dl_items.get(did)
            if card:
                Clock.schedule_once(lambda dt: (
                    card.update(f"❌ {str(e)[:65]}", 0),
                    setattr(card.status_lbl,'color', ORANGE)
                ))
        finally:
            Clock.schedule_once(lambda dt: self._re_enable())

    # ── Helpers ───────────────────────────────────────────
    def _open_login(self):
        LoginPopup(on_done=self.acc_bar.refresh).open()

    def _qf(self, q, f):
        if q == "Audio MP3" or f in ("MP3","M4A"):
            return "bestaudio/best", f.lower()
        qmap = {
            "4K (2160p)": "bestvideo[height<=2160]+bestaudio/best",
            "1080p":       "bestvideo[height<=1080]+bestaudio/best",
            "720p":        "bestvideo[height<=720]+bestaudio/best",
            "480p":        "bestvideo[height<=480]+bestaudio/best",
            "360p":        "bestvideo[height<=360]+bestaudio/best",
            "240p":        "bestvideo[height<=240]+bestaudio/best",
        }
        return qmap.get(q, "best"), f.lower()

    def _re_enable(self):
        self.dl_btn.disabled = False
        url = self.url_inp.text.strip()
        if url.startswith("http"):
            self._on_url(None, url)
        else:
            self.dl_btn.text = "⬇  DOWNLOAD KAREIN"
            self.dl_btn.background_color = ACCENT

    def _popup(self, title, msg):
        c = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
        c.add_widget(Label(text=msg, color=TEXT_W, font_size=dp(13)))
        btn = Button(text="OK", size_hint_y=None, height=dp(40), background_color=ACCENT)
        p = Popup(title=title, content=c, size_hint=(0.85, None), height=dp(160),
            background_color=BG_CARD, title_color=ACCENT)
        btn.bind(on_press=p.dismiss)
        c.add_widget(btn)
        p.open()


# ── App ───────────────────────────────────────────────────
class YTSaverApp(App):
    def build(self):
        self.title = "YTSaver Pro"
        return MainScreen()

if __name__ == "__main__":
    YTSaverApp().run()
