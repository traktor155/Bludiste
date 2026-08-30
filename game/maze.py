# -*- coding: utf-8 -*-
"""Generování bludiště a hledání cesty.

Bludiště je mřížka: 1 = zeď, 0 = chodba.
"""

import random
from collections import deque


def generate_maze(cols, rows, extra_openings=0, rng=None):
    """Vygeneruje bludiště metodou 'recursive backtracker'.

    cols a rows musí být lichá (jinak se zvětší o 1).
    extra_openings = kolik zdí navíc prorazíme, aby vznikly smyčky
    (bez nich jsou v bludišti jen slepé uličky a příšerka je moc zlá).
    """
    rng = rng or random
    if cols % 2 == 0:
        cols += 1
    if rows % 2 == 0:
        rows += 1

    grid = [[1] * cols for _ in range(rows)]
    grid[1][1] = 0
    stack = [(1, 1)]

    while stack:
        x, y = stack[-1]
        options = []
        for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2)):
            nx, ny = x + dx, y + dy
            if 1 <= nx < cols - 1 and 1 <= ny < rows - 1 and grid[ny][nx] == 1:
                options.append((nx, ny, dx, dy))
        if not options:
            stack.pop()
            continue
        nx, ny, dx, dy = rng.choice(options)
        grid[y + dy // 2][x + dx // 2] = 0   # zboříme zeď mezi buňkami
        grid[ny][nx] = 0
        stack.append((nx, ny))

    # prorazíme pár zdí -> vzniknou okružní cesty
    made, tries = 0, 0
    while made < extra_openings and tries < extra_openings * 60:
        tries += 1
        x = rng.randrange(1, cols - 1)
        y = rng.randrange(1, rows - 1)
        if grid[y][x] != 1:
            continue
        vodorovne = (grid[y][x - 1] == 0 and grid[y][x + 1] == 0
                     and grid[y - 1][x] == 1 and grid[y + 1][x] == 1)
        svisle = (grid[y - 1][x] == 0 and grid[y + 1][x] == 0
                  and grid[y][x - 1] == 1 and grid[y][x + 1] == 1)
        if vodorovne or svisle:
            grid[y][x] = 0
            made += 1

    return grid


def free_cells(grid):
    """Seznam všech průchodných buněk."""
    out = []
    for y, row in enumerate(grid):
        for x, v in enumerate(row):
            if v == 0:
                out.append((x, y))
    return out


def distance_map(grid, start):
    """BFS: vzdálenost z 'start' do všech dosažitelných buněk."""
    dist = {start: 0}
    q = deque([start])
    while q:
        x, y = q.popleft()
        d = dist[(x, y)] + 1
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if grid[ny][nx] == 0 and (nx, ny) not in dist:
                dist[(nx, ny)] = d
                q.append((nx, ny))
    return dist


def step_towards(grid, dist_to_target, cell):
    """Z buňky 'cell' vrátí sousední buňku, která je blíž k cíli.

    Používá hotovou mapu vzdáleností (spočítanou BFS z pozice hráče),
    takže i deset příšerek stojí jen jedno BFS za snímek.
    """
    x, y = cell
    here = dist_to_target.get(cell)
    if here is None:
        return None
    best, best_d = None, here
    for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
        if grid[ny][nx] != 0:
            continue
        d = dist_to_target.get((nx, ny))
        if d is not None and d < best_d:
            best, best_d = (nx, ny), d
    return best


def random_free_neighbour(grid, cell, rng=None):
    """Náhodný krok – když příšerka hráče nevidí (neviditelnost)."""
    rng = rng or random
    x, y = cell
    opts = [(nx, ny) for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
            if grid[ny][nx] == 0]
    return rng.choice(opts) if opts else None
