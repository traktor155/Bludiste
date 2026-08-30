# -*- coding: utf-8 -*-
"""Zvuky si hra vyrobí sama za běhu, přímo v paměti.

Nemusíš tak nikde stahovat žádné soubory. Funguje to i v prohlížeči
(pygbag/WASM), kde by zápis WAV souborů přes modul 'wave' nešel.
"""

import math
import struct

import pygame

SR = 22050


def _tone(freq, dur, vol=0.5, shape="sine"):
    n = int(SR * dur)
    out = []
    for i in range(n):
        t = i / SR
        ph = 2 * math.pi * freq * t
        if shape == "square":
            v = 1.0 if math.sin(ph) >= 0 else -1.0
        elif shape == "saw":
            v = 2 * ((freq * t) % 1.0) - 1.0
        else:
            v = math.sin(ph)
        # obálka – rychlý náběh, plynulé doznění (ať to necvaká)
        env = min(1.0, i / (SR * 0.01)) * (1.0 - i / n) ** 1.5
        out.append(v * env * vol)
    return out


def _sweep(f0, f1, dur, vol=0.5, shape="sine"):
    n = int(SR * dur)
    out, ph = [], 0.0
    for i in range(n):
        f = f0 + (f1 - f0) * (i / n)
        ph += 2 * math.pi * f / SR
        v = (1.0 if math.sin(ph) >= 0 else -1.0) if shape == "square" else math.sin(ph)
        env = min(1.0, i / (SR * 0.01)) * (1.0 - i / n) ** 1.2
        out.append(v * env * vol)
    return out


def _pcm_bytes(samples):
    """Převede vzorky (-1..1) na 16bit mono PCM, přesně jak to čeká mixer."""
    return b"".join(struct.pack("<h", max(-32767, min(32767, int(s * 32767))))
                    for s in samples)


def _recipes():
    return {
        "coin": _tone(1046, 0.07, 0.4, "square") + _tone(1568, 0.10, 0.35, "square"),
        "key": (_tone(659, 0.09, 0.4) + _tone(880, 0.09, 0.4)
                + _tone(1319, 0.20, 0.45)),
        "power": _sweep(400, 1400, 0.28, 0.4, "square"),
        "caught": _sweep(700, 160, 0.40, 0.45, "square") + _tone(140, 0.15, 0.3, "saw"),
        "level": (_tone(523, 0.10, 0.4) + _tone(659, 0.10, 0.4)
                  + _tone(784, 0.10, 0.4) + _tone(1046, 0.30, 0.45)),
        "over": _sweep(440, 110, 0.7, 0.4, "saw"),
    }


class SoundBank:
    def __init__(self):
        self.enabled = False
        self.sfx = {}
        try:
            pygame.mixer.init(frequency=SR, size=-16, channels=1, buffer=512)
            for name, samples in _recipes().items():
                self.sfx[name] = pygame.mixer.Sound(buffer=_pcm_bytes(samples))
            self.enabled = True
        except Exception as e:      # bez zvukovky se hraje dál, jen mlčky
            print("Zvuk není dostupný:", e)

    def play(self, name):
        if self.enabled and name in self.sfx:
            self.sfx[name].play()
