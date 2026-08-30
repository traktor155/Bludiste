# -*- coding: utf-8 -*-
"""Zvuky si hra vyrobí sama do assets/sfx při prvním spuštění.

Nemusíš tak nikde stahovat WAV soubory. Když chceš vlastní zvuky,
prostě soubory v assets/sfx přepiš.
"""

import math
import os
import struct
import wave

import pygame

SR = 22050
SFX_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "sfx")


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


def _save(path, samples):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        frames = b"".join(struct.pack("<h", max(-32767, min(32767, int(s * 32767))))
                          for s in samples)
        w.writeframes(frames)


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


def ensure_files():
    os.makedirs(SFX_DIR, exist_ok=True)
    missing = {k: v for k, v in _recipes().items()
               if not os.path.exists(os.path.join(SFX_DIR, k + ".wav"))}
    for name, samples in missing.items():
        _save(os.path.join(SFX_DIR, name + ".wav"), samples)


class SoundBank:
    def __init__(self):
        self.enabled = False
        self.sfx = {}
        try:
            pygame.mixer.init(frequency=SR, size=-16, channels=1, buffer=512)
            ensure_files()
            for name in _recipes():
                p = os.path.join(SFX_DIR, name + ".wav")
                if os.path.exists(p):
                    self.sfx[name] = pygame.mixer.Sound(p)
            self.enabled = True
        except Exception as e:      # bez zvukovky se hraje dál, jen mlčky
            print("Zvuk není dostupný:", e)

    def play(self, name):
        if self.enabled and name in self.sfx:
            self.sfx[name].play()
