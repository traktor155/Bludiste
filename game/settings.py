# -*- coding: utf-8 -*-
"""Konfigurace hry na jednom místě. Klidně si tu měň čísla a hraj si."""

SCREEN_W, SCREEN_H = 960, 720
HUD_H = 72
PAD = 12
FPS = 60

# --- Supabase (leaderboard) ---
SUPABASE_URL = "https://qurenxljgnvdwrjqoxve.supabase.co"
SUPABASE_ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF1cmVueGxqZ252ZHdyanFveHZlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODgxOTc0NzQsImV4cCI6MjEwMzc3MzQ3NH0."
    "44Ai4vwRssS_XIC7fpPSfGe0zeqFHmGUq4tklPtKENM"
)

# --- obtížnost ---
LIVES = 3
PLAYER_SPEED = 5.0          # buňky za sekundu
MONSTER_SPEED_BASE = 2.1    # v 1. kole
MONSTER_SPEED_STEP = 0.28   # o kolik zrychlí každé kolo
MONSTER_SPEED_MAX = 4.4     # aby to zůstalo hratelné pro děti
GRACE_SEC = 1.6             # po chycení příšerky chvíli stojí

DARK_FROM_LEVEL = 4         # od kterého kola "zhasnou světla"
DARK_RADIUS = 4.2           # v buňkách

# rozměry bludiště (musí být lichá čísla)
MAZE_MIN_COLS, MAZE_MIN_ROWS = 11, 9
MAZE_MAX_COLS, MAZE_MAX_ROWS = 27, 19

# --- body ---
PTS_COIN = 10
PTS_KEY = 50
PTS_LEVEL = 100

# --- barvy ---
C_BG = (18, 22, 40)
C_HUD = (28, 34, 60)
C_TEXT = (238, 242, 255)
C_DIM = (150, 160, 190)
C_FLOOR = (36, 44, 78)
C_ACCENT = (255, 209, 102)
C_GREEN = (106, 214, 143)
C_RED = (239, 108, 118)
C_BLUE = (94, 170, 255)
C_PINK = (245, 133, 191)

# paleta zdí – každé kolo jiná barva, ať je to veselé
WALL_PALETTE = [
    (86, 132, 255), (106, 190, 120), (240, 150, 90),
    (196, 120, 230), (90, 200, 210), (235, 120, 140),
]

# druhy příšerek (jen kosmetika + jméno)
MONSTERS = [
    ("Duch", (225, 230, 255)),
    ("Sliz", (130, 220, 120)),
    ("Strašidelná kočka", (255, 170, 90)),
    ("Dráček", (255, 120, 150)),
]

# bonusy
POWER_TYPES = ["speed", "freeze", "invis"]
POWER_DURATION = {"speed": 6.0, "freeze": 4.0, "invis": 5.0}
POWER_LABEL = {"speed": "Zrychlení!", "freeze": "Příšerka zmrzla!", "invis": "Neviditelnost!"}
POWER_COLOR = {"speed": C_BLUE, "freeze": (150, 230, 255), "invis": C_PINK}
