# -*- coding: utf-8 -*-
"""Hráč, příšerky, předměty – pohyb i vykreslování."""

import math
import pygame

from maze import step_towards, random_free_neighbour


class Mover:
    """Pohyb po buňkách s plynulou animací mezi nimi.

    Díky tomu nikdy nezasekneš v chodbě jako u pohybu po pixelech.
    """

    def __init__(self, cell, speed):
        self.cx, self.cy = cell
        self.tx, self.ty = cell
        self.t = 0.0            # 0..1 = kde jsme mezi buňkami
        self.speed = speed      # buněk za sekundu
        self.moving = False
        self.facing = (0, 1)

    def try_step(self, grid, dx, dy):
        self.facing = (dx, dy)
        if self.moving:
            return False
        nx, ny = self.cx + dx, self.cy + dy
        if grid[ny][nx] == 0:
            self.tx, self.ty = nx, ny
            self.moving = True
            self.t = 0.0
            return True
        return False

    def goto(self, cell):
        if self.moving or cell is None:
            return False
        self.tx, self.ty = cell
        self.facing = (self.tx - self.cx, self.ty - self.cy)
        self.moving = True
        self.t = 0.0
        return True

    def update(self, dt, speed_mult=1.0):
        """Vrací True, když právě dorazil do nové buňky."""
        if not self.moving:
            return False
        self.t += dt * self.speed * speed_mult
        if self.t >= 1.0:
            self.cx, self.cy = self.tx, self.ty
            self.t = 0.0
            self.moving = False
            return True
        return False

    def fpos(self):
        """Plynulá pozice v souřadnicích buněk (float)."""
        if not self.moving:
            return float(self.cx), float(self.cy)
        return (self.cx + (self.tx - self.cx) * self.t,
                self.cy + (self.ty - self.cy) * self.t)

    def cell(self):
        return (self.cx, self.cy)


class Player(Mover):
    def __init__(self, cell, speed):
        super().__init__(cell, speed)
        self.has_key = False
        self.anim = 0.0

    def handle_input(self, grid, keys, dt):
        self.anim += dt
        if self.moving:
            return
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.try_step(grid, -1, 0)
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.try_step(grid, 1, 0)
        elif keys[pygame.K_UP] or keys[pygame.K_w]:
            self.try_step(grid, 0, -1)
        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.try_step(grid, 0, 1)

    def draw(self, surf, px, py, r):
        hop = math.sin(self.anim * 10) * (r * 0.10 if self.moving else 0)
        cy = py - hop
        pygame.draw.circle(surf, (255, 224, 130), (int(px), int(cy)), r)
        pygame.draw.circle(surf, (232, 180, 70), (int(px), int(cy)), r, max(2, r // 8))
        # oči se koukají tam, kam jdeme
        ox = self.facing[0] * r * 0.16
        oy = self.facing[1] * r * 0.14
        for s in (-1, 1):
            ex = px + s * r * 0.34 + ox
            ey = cy - r * 0.12 + oy
            pygame.draw.circle(surf, (255, 255, 255), (int(ex), int(ey)), max(2, int(r * 0.22)))
            pygame.draw.circle(surf, (40, 40, 60), (int(ex), int(ey)), max(1, int(r * 0.11)))
        # úsměv
        rect = pygame.Rect(0, 0, r, r * 0.7)
        rect.center = (px, cy + r * 0.28)
        pygame.draw.arc(surf, (150, 90, 40), rect, math.pi * 1.15, math.pi * 1.85, max(2, r // 9))
        if self.has_key:
            pygame.draw.circle(surf, (255, 215, 80), (int(px + r * 0.8), int(cy - r * 0.8)),
                               max(2, int(r * 0.24)))


class Monster(Mover):
    def __init__(self, cell, speed, kind, color):
        super().__init__(cell, speed)
        self.kind = kind
        self.color = color
        self.anim = 0.0
        self.frozen = 0.0       # zbývající sekundy zmrazení
        self.confused = 0.0     # hráč je neviditelný -> chodí naslepo

    def think(self, grid, dist_map, rng):
        if self.moving:
            return
        target = None
        if self.confused <= 0:
            target = step_towards(grid, dist_map, self.cell())
        if target is None:
            target = random_free_neighbour(grid, self.cell(), rng)
        self.goto(target)

    def update_ai(self, dt, grid, dist_map, rng):
        self.anim += dt
        self.frozen = max(0.0, self.frozen - dt)
        self.confused = max(0.0, self.confused - dt)
        if self.frozen > 0:
            return
        self.think(grid, dist_map, rng)
        self.update(dt)

    def draw(self, surf, px, py, r):
        col = self.color
        if self.frozen > 0:
            col = (150, 225, 255)
        wob = math.sin(self.anim * 6) * r * 0.08
        cy = py + wob * 0.3

        if self.kind == "Duch":
            pygame.draw.circle(surf, col, (int(px), int(cy)), r)
            pygame.draw.rect(surf, col, (px - r, cy, r * 2, r * 0.75))
            for i in range(4):   # vlnitý spodek
                bx = px - r + r * 0.5 * i + r * 0.25
                pygame.draw.circle(surf, col, (int(bx), int(cy + r * 0.75)), int(r * 0.26))
        elif self.kind == "Sliz":
            pygame.draw.ellipse(surf, col, (px - r, cy - r * 0.65, r * 2, r * 1.55))
            pygame.draw.circle(surf, col, (int(px - r * 0.5), int(cy + r * 0.8)), int(r * 0.2))
        elif self.kind == "Strašidelná kočka":
            pygame.draw.circle(surf, col, (int(px), int(cy)), r)
            for s in (-1, 1):   # ouška
                pygame.draw.polygon(surf, col, [
                    (px + s * r * 0.75, cy - r * 0.55),
                    (px + s * r * 0.30, cy - r * 1.15),
                    (px + s * r * 0.15, cy - r * 0.50)])
        else:  # Dráček
            pygame.draw.circle(surf, col, (int(px), int(cy)), r)
            for s in (-1, 1):   # růžky
                pygame.draw.polygon(surf, (255, 240, 200), [
                    (px + s * r * 0.55, cy - r * 0.70),
                    (px + s * r * 0.35, cy - r * 1.25),
                    (px + s * r * 0.15, cy - r * 0.65)])

        ox = self.facing[0] * r * 0.14
        for s in (-1, 1):
            ex, ey = px + s * r * 0.35 + ox, cy - r * 0.10
            pygame.draw.circle(surf, (255, 255, 255), (int(ex), int(ey)), max(2, int(r * 0.24)))
            pygame.draw.circle(surf, (45, 45, 70), (int(ex + ox), int(ey)), max(1, int(r * 0.12)))
        rect = pygame.Rect(0, 0, r * 0.9, r * 0.6)
        rect.center = (px, cy + r * 0.30)
        pygame.draw.arc(surf, (60, 50, 80), rect, math.pi * 1.15, math.pi * 1.85, max(2, r // 10))


class Item:
    """Sbíratelná věc: coin / key / exit / power_*"""

    def __init__(self, cell, kind):
        self.cell = cell
        self.kind = kind
        self.taken = False
        self.anim = 0.0

    def draw(self, surf, px, py, r, has_key=False):
        self.anim += 0.05
        bob = math.sin(self.anim * 2) * r * 0.12

        if self.kind == "coin":
            pygame.draw.circle(surf, (255, 205, 70), (int(px), int(py + bob)), int(r * 0.42))
            pygame.draw.circle(surf, (255, 240, 170), (int(px), int(py + bob)), int(r * 0.42), 2)
        elif self.kind == "star":
            _star(surf, px, py + bob, r * 0.5, (255, 235, 120))
        elif self.kind == "key":
            y = py + bob
            pygame.draw.circle(surf, (255, 220, 90), (int(px - r * 0.18), int(y)), int(r * 0.26), 3)
            pygame.draw.line(surf, (255, 220, 90), (px, y), (px + r * 0.5, y), 3)
            pygame.draw.line(surf, (255, 220, 90), (px + r * 0.45, y),
                             (px + r * 0.45, y + r * 0.25), 3)
        elif self.kind == "exit":
            col = (110, 225, 150) if has_key else (120, 130, 165)
            pygame.draw.rect(surf, col, (px - r * 0.55, py - r * 0.75, r * 1.1, r * 1.5),
                             border_radius=int(r * 0.25))
            pygame.draw.rect(surf, (30, 40, 60), (px - r * 0.35, py - r * 0.55, r * 0.7, r * 1.1),
                             border_radius=int(r * 0.2))
            if not has_key:
                pygame.draw.circle(surf, (255, 220, 90), (int(px), int(py)), int(r * 0.18), 2)
        else:  # bonusy
            from settings import POWER_COLOR
            col = POWER_COLOR.get(self.kind.replace("power_", ""), (200, 200, 255))
            pygame.draw.circle(surf, col, (int(px), int(py + bob)), int(r * 0.40))
            pygame.draw.circle(surf, (255, 255, 255), (int(px), int(py + bob)), int(r * 0.40), 2)
            pygame.draw.circle(surf, (255, 255, 255), (int(px), int(py + bob)), int(r * 0.14))


def _star(surf, cx, cy, r, col):
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rad = r if i % 2 == 0 else r * 0.45
        pts.append((cx + math.cos(ang) * rad, cy + math.sin(ang) * rad))
    pygame.draw.polygon(surf, col, pts)
