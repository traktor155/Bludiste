# -*- coding: utf-8 -*-
"""Komunikace se Supabase (leaderboard).

Na desktopu jde přes standardní urllib (žádná externí závislost).
V prohlížeči (pygbag/WASM) přes vestavěný aio.fetch (skutečné vlákna ani
sockety tam nejsou). Když síť/Supabase nejede, skóre se uloží lokálně do
souboru a hra jede dál – dítě nesmí přijít o body kvůli výpadku sítě.
"""

import asyncio
import json
import os
import sys
import threading
import urllib.error
import urllib.request

from settings import SUPABASE_ANON_KEY, SUPABASE_URL

HOME = os.path.join(os.path.expanduser("~"), ".utek_pred_priserkou")
LOCAL_SCORES = os.path.join(HOME, "local_scores.json")
NAME_FILE = os.path.join(HOME, "name.txt")
TIMEOUT = 2.5

SCORES_URL = SUPABASE_URL.rstrip("/") + "/rest/v1/scores"
LEADERBOARD_URL = SUPABASE_URL.rstrip("/") + "/rest/v1/leaderboard_best"

# V prohlížeči (pygbag/WASM) nejsou skutečná vlákna ani sockety – síť
# se tam posílá přes JS Fetch API (modul 'aio.fetch', dostupný jen tam).
WEB = sys.platform == "emscripten"


def _looks_like_error(text):
    """Supabase/PostgREST chybu vrací jako JSON objekt s klíčem 'message'."""
    if not text:
        return False
    try:
        parsed = json.loads(text)
    except ValueError:
        return False
    return isinstance(parsed, dict) and "message" in parsed


class ApiClient:
    def __init__(self):
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
            asyncio.create_task(self._post_score_web(name, score, level, done))
            return None
        t = threading.Thread(target=self._post_score, args=(name, score, level, done),
                             daemon=True)
        t.start()
        return t

    def _post_score(self, name, score, level, done):
        payload = json.dumps({"name": name, "score": int(score), "level": int(level)}
                             ).encode("utf-8")
        req = urllib.request.Request(
            SCORES_URL, data=payload, method="POST",
            headers={"Content-Type": "application/json",
                     "apikey": SUPABASE_ANON_KEY,
                     "Prefer": "return=minimal"})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT):
                pass
            ok = True
            self.last_error = None
        except Exception as e:
            ok = False
            self.last_error = str(e)
            self._store_local(name, score, level)
        if done:
            done(ok)

    async def _post_score_web(self, name, score, level, done):
        import aio.fetch
        ok = False
        try:
            url = "%s?apikey=%s" % (SCORES_URL, SUPABASE_ANON_KEY)
            rh = aio.fetch.RequestHandler()
            result = await rh.post(url, {"name": name, "score": int(score),
                                         "level": int(level)})
            ok = not _looks_like_error(result)
        except Exception as e:
            self.last_error = str(e)
        if not ok:
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
            asyncio.create_task(self._leaderboard_web(done, limit))
            return
        threading.Thread(target=self._leaderboard, args=(done, limit), daemon=True).start()

    def _leaderboard(self, done, limit):
        url = "%s?select=name,score,level,created_at&order=score.desc&limit=%d" % (
            LEADERBOARD_URL, limit)
        req = urllib.request.Request(url, headers={"apikey": SUPABASE_ANON_KEY})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                rows = json.load(r)
            done(rows, True)
        except Exception as e:
            self.last_error = str(e)
            done(self.local_scores()[:limit], False)

    async def _leaderboard_web(self, done, limit):
        import aio.fetch
        try:
            url = "%s?apikey=%s&select=name,score,level,created_at&order=score.desc&limit=%d" % (
                LEADERBOARD_URL, SUPABASE_ANON_KEY, limit)
            rh = aio.fetch.RequestHandler()
            result = await rh.get(url)
            if _looks_like_error(result):
                raise RuntimeError(result)
            done(json.loads(result), True)
        except Exception as e:
            self.last_error = str(e)
            done(self.local_scores()[:limit], False)
