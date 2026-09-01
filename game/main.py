# -*- coding: utf-8 -*-
"""ÚNIK PŘED PŘÍŠERKOU – bludišťová hra pro děti.

Spuštění:   python main.py
Test bez okna: python main.py --smoke 900
"""

import asyncio
import collections
import math
import random
import sys

import pygame

from api_client import ApiClient
from entities import Item, Monster, Player
from maze import distance_map, free_cells, generate_maze
from settings import *
from sounds import SoundBank

MENU, PLAY, CAUGHT, LEVELUP, OVER, BOARD = range(6)


class Level:
    """Jedno kolo: bludiště, předměty, příšerky."""

    def __init__(self, number, rng):
        self.number = number
        self.rng = rng
        self.cols = min(MAZE_MAX_COLS, MAZE_MIN_COLS + 2 * (number - 1))
        self.rows = min(MAZE_MAX_ROWS, MAZE_MIN_ROWS + 2 * (number - 1))
        # zkratky/smyčky ať rostou s plochou bludiště, ne jen s číslem kola –
        # jinak je bludiště od vyšších kol (kdy se blíží maximální velikosti)
        # relativně nejřidší a hráč se snáz zaklíní do slepé uličky s příšerkou
        extra_openings = max(2 + number, (self.cols * self.rows) // 22)
        self.grid = generate_maze(self.cols, self.rows, extra_openings=extra_openings, rng=rng)
        self.cols = len(self.grid[0])
        self.rows = len(self.grid)
        self.wall_color = WALL_PALETTE[(number - 1) % len(WALL_PALETTE)]
        self.dark = number >= DARK_FROM_LEVEL

        # rozměry na obrazovce – dlaždice se přizpůsobí, aby se bludiště vešlo
        self.tile = min((SCREEN_W - 2 * PAD) // self.cols,
                        (SCREEN_H - HUD_H - 2 * PAD) // self.rows)
        self.ox = (SCREEN_W - self.cols * self.tile) // 2
        self.oy = HUD_H + (SCREEN_H - HUD_H - self.rows * self.tile) // 2

        self.start = (1, 1)
        dist = distance_map(self.grid, self.start)
        far = max(dist.values())
        self.exit_cell = max(dist, key=lambda c: dist[c])

        cells = [c for c in free_cells(self.grid) if c not in (self.start, self.exit_cell)]
        rng.shuffle(cells)

        # klíč dáme doprostřed obtížnosti – ne hned u startu, ne až u východu
        key_pool = [c for c in cells if 0.35 * far <= dist[c] <= 0.85 * far] or cells
        self.key_cell = rng.choice(key_pool)

        pool = [c for c in cells if c != self.key_cell]
        n_coins = min(len(pool), 5 + number * 2)
        self.items = [Item(self.key_cell, "key"), Item(self.exit_cell, "exit")]
        for c in pool[:n_coins]:
            self.items.append(Item(c, "star" if rng.random() < 0.25 else "coin"))
        rest = pool[n_coins:]
        for i in range(min(len(rest), 1 + number // 3)):
            self.items.append(Item(rest[i], "power_" + rng.choice(POWER_TYPES)))

        # příšerky – vždy dost daleko od hráče
        speed = min(MONSTER_SPEED_MAX, MONSTER_SPEED_BASE + MONSTER_SPEED_STEP * (number - 1))
        spots = [c for c in cells if dist[c] >= 0.6 * far] or cells
        rng.shuffle(spots)
        self.monsters = []
        for i in range(min(len(spots), 4, 1 + (number - 1) // 3)):
            kind, color = MONSTERS[(number - 1 + i) % len(MONSTERS)]
            self.monsters.append(Monster(spots[i], speed, kind, color))
        self.monster_home = [m.cell() for m in self.monsters]

    def coins_left(self):
        return sum(1 for it in self.items
                   if it.kind in ("coin", "star") and not it.taken)

    def to_px(self, fx, fy):
        return (self.ox + (fx + 0.5) * self.tile, self.oy + (fy + 0.5) * self.tile)


class Game:
    def __init__(self, smoke=0):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("Únik před příšerkou")
        self.clock = pygame.time.Clock()
        self.rng = random.Random()
        self.sounds = SoundBank()
        self.api = ApiClient()
        self.overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)

        path = pygame.font.match_font("dejavusans,freesans,arial,liberationsans")
        self.fonts = {}
        self._font_path = path

        self.name = self.api.load_name()
        self.state = MENU
        self.smoke = smoke
        self.frame = 0
        self.msg = ""
        self.msg_t = 0.0
        self.board_rows, self.board_online = [], False
        self.sent = None
        self.reset_run()

    # ---------------- pomůcky ----------------
    def font(self, size, bold=False):
        k = (size, bold)
        if k not in self.fonts:
            f = pygame.font.Font(self._font_path, size) if self._font_path \
                else pygame.font.Font(None, int(size * 1.15))
            f.set_bold(bold)
            self.fonts[k] = f
        return self.fonts[k]

    def text(self, s, size, color=C_TEXT, center=None, topleft=None, bold=False):
        img = self.font(size, bold).render(s, True, color)
        r = img.get_rect()
        if center:
            r.center = center
        else:
            r.topleft = topleft or (0, 0)
        self.screen.blit(img, r)
        return r

    def flash(self, s, seconds=1.6):
        self.msg, self.msg_t = s, seconds

    # ---------------- běh hry ----------------
    def reset_run(self):
        self.score = 0
        self.level_no = 1
        self.lives = LIVES
        self.level = None
        self.power = {}

    def start_run(self):
        self.reset_run()
        self.new_level()
        self.state = PLAY

    def new_level(self):
        self.level = Level(self.level_no, self.rng)
        self.spawn_player()
        self.elapsed = 0.0
        self.power = {}

    def spawn_player(self):
        lv = self.level
        self.player = Player(lv.start, PLAYER_SPEED)
        self.player.has_key = any(it.kind == "key" and it.taken for it in lv.items)
        for m, home in zip(lv.monsters, lv.monster_home):
            m.cx, m.cy = home
            m.tx, m.ty = home
            m.moving, m.t = False, 0.0
            m.frozen = GRACE_SEC
            m.confused = 0.0

    def add_power(self, kind):
        self.power[kind] = POWER_DURATION[kind]
        if kind == "freeze":
            for m in self.level.monsters:
                m.frozen = max(m.frozen, POWER_DURATION["freeze"])
        if kind == "invis":
            for m in self.level.monsters:
                m.confused = max(m.confused, POWER_DURATION["invis"])
        self.flash(POWER_LABEL[kind])
        self.sounds.play("power")

    def update_play(self, dt, keys):
        lv = self.level
        self.elapsed += dt
        for k in list(self.power):
            self.power[k] -= dt
            if self.power[k] <= 0:
                del self.power[k]

        mult = 1.55 if "speed" in self.power else 1.0
        self.player.handle_input(lv.grid, keys, dt)
        self.player.update(dt, mult)

        # sbírání – jednou za snímek podle buňky, na které hráč stojí
        pcell = self.player.cell()
        for it in lv.items:
            if it.taken or it.cell != pcell:
                continue
            if it.kind in ("coin", "star"):
                it.taken = True
                self.score += PTS_COIN * (2 if it.kind == "star" else 1)
                self.sounds.play("coin")
            elif it.kind == "key":
                it.taken = True
                self.player.has_key = True
                self.score += PTS_KEY
                self.sounds.play("key")
                self.flash("Máš klíč! Běž k východu.")
            elif it.kind.startswith("power_"):
                it.taken = True
                self.add_power(it.kind.split("_", 1)[1])
            elif it.kind == "exit" and self.player.has_key and not self.player.moving:
                self.finish_level()
                return

        # příšerky
        dist_map = distance_map(lv.grid, pcell)
        for m in lv.monsters:
            m.update_ai(dt, lv.grid, dist_map, self.rng)

        # chycení
        px, py = self.player.fpos()
        for m in lv.monsters:
            if m.frozen > 0:
                continue
            mx, my = m.fpos()
            if math.hypot(px - mx, py - my) < 0.62:
                self.caught_by = m.kind
                self.lives -= 1
                self.sounds.play("caught")
                if self.lives <= 0:
                    self.sounds.play("over")
                    self.sent = None
                    self.api.post_score_async(self.name or "Hráč", self.score, self.level_no,
                                              done=self._on_sent)
                    self.state = OVER
                else:
                    self.state = CAUGHT
                return

    def _on_sent(self, ok):
        self.sent = ok

    def finish_level(self):
        bonus = max(0, int(300 - self.elapsed * 4))
        self.level_bonus = bonus
        self.score += PTS_LEVEL + bonus
        self.sounds.play("level")
        self.state = LEVELUP

    # ---------------- kreslení ----------------
    def draw_maze(self):
        lv, t = self.level, self.level.tile
        pygame.draw.rect(self.screen, C_FLOOR,
                         (lv.ox, lv.oy, lv.cols * t, lv.rows * t), border_radius=8)
        for y in range(lv.rows):
            for x in range(lv.cols):
                if lv.grid[y][x] == 1:
                    r = pygame.Rect(lv.ox + x * t, lv.oy + y * t, t, t)
                    pygame.draw.rect(self.screen, lv.wall_color, r, border_radius=max(3, t // 6))
                    pygame.draw.rect(self.screen, (255, 255, 255, 40), r, 1,
                                     border_radius=max(3, t // 6))

    def draw_dark(self):
        px, py = self.level.to_px(*self.player.fpos())
        self.overlay.fill((4, 6, 16, 240))
        r = int(DARK_RADIUS * self.level.tile)
        for i in range(10):          # měkký okraj světla
            a = int(240 * (i / 10) ** 2)
            pygame.draw.circle(self.overlay, (4, 6, 16, a), (int(px), int(py)),
                               int(r * (1 - i / 12)))
        pygame.draw.circle(self.overlay, (4, 6, 16, 0), (int(px), int(py)), int(r * 0.55))
        self.screen.blit(self.overlay, (0, 0))

    def draw_hud(self):
        pygame.draw.rect(self.screen, C_HUD, (0, 0, SCREEN_W, HUD_H))
        self.text("Kolo %d" % self.level_no, 24, C_ACCENT, topleft=(PAD + 6, 10), bold=True)
        self.text("%d bodů" % self.score, 20, C_TEXT, topleft=(PAD + 6, 40))

        for i in range(LIVES):       # srdíčka
            cx = 200 + i * 30
            col = C_RED if i < self.lives else (70, 78, 105)
            pygame.draw.circle(self.screen, col, (cx - 5, 26), 7)
            pygame.draw.circle(self.screen, col, (cx + 5, 26), 7)
            pygame.draw.polygon(self.screen, col, [(cx - 11, 30), (cx + 11, 30), (cx, 44)])

        key_col = C_ACCENT if self.player.has_key else (80, 88, 115)
        self.text("klíč", 18, key_col, topleft=(200, 46))
        self.text("hvězdičky: %d" % self.level.coins_left(), 18, C_DIM, topleft=(300, 46))
        if self.level.dark:
            self.text("Světla zhasla!", 18, C_PINK, topleft=(300, 20))

        x = 520
        for kind, left in self.power.items():
            col = POWER_COLOR[kind]
            self.text(POWER_LABEL[kind].rstrip("!"), 16, col, topleft=(x, 14))
            w = int(120 * min(1.0, left / POWER_DURATION[kind]))
            pygame.draw.rect(self.screen, (60, 68, 95), (x, 36, 120, 8), border_radius=4)
            pygame.draw.rect(self.screen, col, (x, 36, w, 8), border_radius=4)
            x += 140

        self.text("čas %ds" % int(self.elapsed), 18, C_DIM, topleft=(SCREEN_W - 110, 40))
        if self.msg_t > 0:
            self.text(self.msg, 22, C_GREEN, center=(SCREEN_W // 2, 26), bold=True)

    def draw_world(self):
        self.screen.fill(C_BG)
        self.draw_maze()
        lv, t = self.level, self.level.tile
        r = t // 2 - 2
        for it in lv.items:
            if it.taken:
                continue
            px, py = lv.to_px(*it.cell)
            it.draw(self.screen, px, py, r, self.player.has_key)
        for m in lv.monsters:
            px, py = lv.to_px(*m.fpos())
            m.draw(self.screen, px, py, int(r * 0.92))
        px, py = lv.to_px(*self.player.fpos())
        self.player.draw(self.screen, px, py, int(r * 0.88))
        if lv.dark:
            self.draw_dark()
        self.draw_hud()

    def panel(self, lines, hint=None):
        """Poloprůhledné okno s textem přes hru."""
        self.overlay.fill((10, 14, 30, 205))
        self.screen.blit(self.overlay, (0, 0))
        y = SCREEN_H // 2 - 30 * len(lines)
        for i, (s, size, col) in enumerate(lines):
            self.text(s, size, col, center=(SCREEN_W // 2, y), bold=(i == 0))
            y += size + 18
        if hint:
            self.text(hint, 20, C_DIM, center=(SCREEN_W // 2, SCREEN_H - 60))

    def draw_menu(self):
        self.screen.fill(C_BG)
        self.text("ÚNIK PŘED PŘÍŠERKOU", 54, C_ACCENT,
                  center=(SCREEN_W // 2, 150), bold=True)
        self.text("Najdi klíč, seber hvězdičky a uteč k východu!", 24, C_TEXT,
                  center=(SCREEN_W // 2, 215))
        self.text("Jak se jmenuješ?", 24, C_DIM, center=(SCREEN_W // 2, 320))
        box = pygame.Rect(SCREEN_W // 2 - 180, 350, 360, 56)
        pygame.draw.rect(self.screen, C_HUD, box, border_radius=10)
        pygame.draw.rect(self.screen, C_BLUE, box, 2, border_radius=10)
        caret = "|" if (self.frame // 30) % 2 == 0 else " "
        self.text((self.name or "") + caret, 30, C_TEXT, center=box.center)
        self.text("ENTER = hrát     šipky = pohyb     TAB = žebříček     ESC = konec",
                  20, C_DIM, center=(SCREEN_W // 2, 470))
        self.text("Chytí-li tě příšerka, jen tě polechtá a přijdeš o srdíčko.",
                  18, C_DIM, center=(SCREEN_W // 2, 520))

    def draw_board(self):
        self.screen.fill(C_BG)
        self.text("NEJLEPŠÍ HRÁČI", 44, C_ACCENT, center=(SCREEN_W // 2, 90), bold=True)
        src = "online žebříček" if self.board_online else "offline – lokální skóre"
        self.text(src, 18, C_DIM, center=(SCREEN_W // 2, 130))
        if not self.board_rows:
            self.text("Zatím tu nikdo není. Buď první!", 24, C_TEXT,
                      center=(SCREEN_W // 2, 300))
        for i, row in enumerate(self.board_rows[:10]):
            y = 190 + i * 42
            col = C_ACCENT if i == 0 else C_TEXT
            self.text("%d." % (i + 1), 26, col, topleft=(300, y))
            self.text(str(row.get("name", "?"))[:18], 26, col, topleft=(350, y))
            self.text(str(row.get("score", 0)), 26, col, topleft=(600, y))
        self.text("ESC = zpět", 20, C_DIM, center=(SCREEN_W // 2, SCREEN_H - 50))

    # ---------------- události ----------------
    def on_key(self, e):
        if self.state == MENU:
            if e.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and self.name.strip():
                self.api.save_name(self.name.strip())
                self.start_run()
            elif e.key == pygame.K_BACKSPACE:
                self.name = self.name[:-1]
            elif e.key == pygame.K_ESCAPE:
                return False
            elif e.key == pygame.K_TAB:
                self.open_board()
            elif e.unicode and e.unicode.isprintable() and len(self.name) < 18:
                self.name += e.unicode
        elif self.state == PLAY:
            if e.key == pygame.K_ESCAPE:
                if self.score > 0:
                    self.api.post_score_async(self.name or "Hráč", self.score, self.level_no)
                self.state = MENU
        elif self.state == CAUGHT:
            if e.key in (pygame.K_SPACE, pygame.K_RETURN):
                self.spawn_player()
                self.state = PLAY
        elif self.state == LEVELUP:
            if e.key in (pygame.K_SPACE, pygame.K_RETURN):
                self.level_no += 1
                self.new_level()
                self.state = PLAY
        elif self.state == OVER:
            if e.key in (pygame.K_SPACE, pygame.K_RETURN):
                self.open_board()
            elif e.key == pygame.K_ESCAPE:
                self.state = MENU
        elif self.state == BOARD:
            if e.key in (pygame.K_ESCAPE, pygame.K_SPACE, pygame.K_RETURN):
                self.state = MENU
        return True

    def open_board(self):
        self.board_rows, self.board_online = [], False
        self.api.leaderboard_async(self._on_board)
        self.state = BOARD

    def _on_board(self, rows, online):
        self.board_rows, self.board_online = rows, online

    # ---------------- hlavní smyčka ----------------
    async def run(self):
        running = True
        while running:
            dt = min(0.05, self.clock.tick(FPS) / 1000.0)
            self.frame += 1
            self.msg_t = max(0.0, self.msg_t - dt)

            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    running = False
                elif e.type == pygame.KEYDOWN:
                    if not self.on_key(e):
                        running = False

            if self.smoke:
                running = self._smoke_tick() and running

            keys = self._keys()
            if self.state == PLAY:
                self.update_play(dt, keys)

            if self.state == MENU:
                self.draw_menu()
            elif self.state == BOARD:
                self.draw_board()
            elif self.state == PLAY:
                self.draw_world()
            elif self.state == CAUGHT:
                self.draw_world()
                self.panel([("Jupí, %s tě polechtal!" % self.caught_by, 40, C_PINK),
                            ("Zbývá ti srdíček: %d" % self.lives, 26, C_TEXT)],
                           "Mezerník = zkusit znovu")
            elif self.state == LEVELUP:
                self.draw_world()
                self.panel([("Utekl jsi! Kolo %d hotovo" % self.level_no, 40, C_GREEN),
                            ("+%d za kolo, +%d za rychlost" % (PTS_LEVEL, self.level_bonus),
                             24, C_TEXT),
                            ("Celkem: %d bodů" % self.score, 28, C_ACCENT)],
                           "Mezerník = další kolo (bude větší a rychlejší!)")
            elif self.state == OVER:
                self.draw_world()
                stav = {True: "Skóre odesláno na server.",
                        False: "Server neběží – skóre uloženo v počítači.",
                        None: "Odesílám skóre…"}[self.sent]
                self.panel([("Konec hry", 46, C_RED),
                            ("Dostal jsi %d bodů a došel do %d. kola." %
                             (self.score, self.level_no), 26, C_TEXT),
                            (stav, 20, C_DIM)],
                           "Mezerník = žebříček     ESC = menu")

            pygame.display.flip()
            await asyncio.sleep(0)
        pygame.quit()

    def _keys(self):
        if not self.smoke:
            return pygame.key.get_pressed()
        return self._fake_keys

    # ---------------- automatický test ----------------
    def _smoke_tick(self):
        """Umí hru 'odehrát' bez člověka – slouží k testování."""
        if self.frame == 1:
            self.name = "Test"
            self.start_run()
        if self.frame % 7 == 0:
            self._fake_keys = collections.defaultdict(bool)
            self._fake_keys[self.rng.choice(
                [pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN])] = True
        if self.state in (CAUGHT, LEVELUP, OVER, BOARD):
            ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE, unicode=" ")
            self.on_key(ev)
            if self.state == BOARD:
                self.state = MENU
                self.start_run()
        return self.frame < self.smoke


async def main():
    smoke = 0
    if "--smoke" in sys.argv:
        i = sys.argv.index("--smoke")
        smoke = int(sys.argv[i + 1]) if len(sys.argv) > i + 1 else 900
    g = Game(smoke=smoke)
    if smoke:
        g._fake_keys = collections.defaultdict(bool)
    await g.run()


if __name__ == "__main__":
    asyncio.run(main())
