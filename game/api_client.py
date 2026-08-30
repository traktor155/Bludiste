# -*- coding: utf-8 -*-
"""Komunikace s FastAPI serverem.

Používá jen standardní knihovnu (urllib), takže hra funguje i bez 'requests'.
Když server neběží, skóre se uloží lokálně do souboru a hra jede dál –
dítě nesmí přijít o body kvůli tomu, že si zapomněl spustit server. :)
"""

import json
import os
import sys
import threading
import urllib.error
import urllib.request

HOME = os.path.join(os.path.expanduser("~"), ".utek_pred_priserkou")
LOCAL_SCORES = os.path.join(HOME, "local_scores.json")
NAME_FILE = os.path.join(HOME, "name.txt")
TIMEOUT = 2.5

# V prohlížeči (pygbag/WASM) nejsou skutečná vlákna ani sockety – síť
# tam nezkoušíme a rovnou použijeme lokální úložiště.
WEB = sys.platform == "emscripten"


class ApiClient:
    def __init__(self, base_url):
        self.base = base_url.rstrip("/")
        self.last_error = None
        os.makedirs(HOME, exist_ok=True)

    # ---------- jméno hráče ----------
    def load_name(self):
        try:
            with open(NAME_FILE, encoding="utf-8") as f:
                return f.read().strip()[:20]
        except OSError:
            return ""

    def save_name(self, name):
        try:
            with open(NAME_FILE, "w", encoding="utf-8") as f:
                f.write(name.strip()[:20])
        except OSError:
            pass

    # ---------- skóre ----------
    def post_score_async(self, name, score, level, done=None):
        """Odešle skóre na pozadí, aby hra nezatuhla na síti."""
        if WEB:
            self._store_local(name, score, level)
            if done:
                done(False)
            return None
        t = threading.Thread(target=self._post_score, args=(name, score, level, done),
                             daemon=True)
        t.start()
        return t

    def _post_score(self, name, score, level, done):
        payload = json.dumps({"name": name, "score": int(score), "level": int(level)}
                             ).encode("utf-8")
        req = urllib.request.Request(
            self.base + "/score", data=payload,
            headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                json.load(r)
            ok = True
            self.last_error = None
        except Exception as e:
            ok = False
            self.last_error = str(e)
            self._store_local(name, score, level)
        if done:
            done(ok)

    def _store_local(self, name, score, level):
        data = self.local_scores()
        data.append({"name": name, "score": int(score), "level": int(level)})
        data.sort(key=lambda r: -r["score"])
        try:
            with open(LOCAL_SCORES, "w", encoding="utf-8") as f:
                json.dump(data[:50], f, ensure_ascii=False, indent=1)
        except OSError:
            pass

    def local_scores(self):
        try:
            with open(LOCAL_SCORES, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return []

    # ---------- žebříček ----------
    def leaderboard_async(self, done, limit=10):
        if WEB:
            done(self.local_scores()[:limit], False)
            return
        threading.Thread(target=self._leaderboard, args=(done, limit), daemon=True).start()

    def _leaderboard(self, done, limit):
        url = "%s/leaderboard?limit=%d" % (self.base, limit)
        try:
            with urllib.request.urlopen(url, timeout=TIMEOUT) as r:
                rows = json.load(r)
            done(rows, True)
        except Exception as e:
            self.last_error = str(e)
            done(self.local_scores()[:limit], False)
