# 🏃 Únik před příšerkou

Bludišťová hra pro děti v Pythonu + Pygame, s leaderboardem na FastAPI + SQLite.
Přesně podle tvého návrhu.

## Co to umí

**Hra (`game/`)**
- Bludiště se generuje pokaždé znovu (algoritmus *recursive backtracker*)
- Sbírání mincí a hvězdiček, klíč odemyká východ
- Příšerka hledá cestu pomocí **BFS** – opravdu bludištěm proplouvá za tebou
- Každé kolo: větší bludiště, rychlejší příšerka, víc příšerek (max 4)
- Mód **„světla zhasla“** od 4. kola – vidíš jen kolem sebe
- Bonusy: zrychlení, zmrazení příšerky, neviditelnost
- Ovládání šipkami (nebo WASD), 3 srdíčka, žádné násilí – příšerka tě jen polechtá
- Zvuky si hra vyrobí sama, nemusíš nic stahovat

**Server (`server/`)**
- `POST /score`, `GET /leaderboard`, `GET /player/{jméno}`, `GET /health`
- SQLite databáze (tabulka `players`)
- Žebříček i jako webová stránka na `/` (sám se obnovuje)
- Automatická dokumentace na `/docs`

Když server neběží, hra funguje dál a skóre si uloží lokálně.

## Instalace

```bash
pip install pygame fastapi uvicorn
```

## Spuštění

Server (v jednom okně terminálu):
```bash
cd server
uvicorn main:app --reload --port 8000
```

Hra (v druhém okně):
```bash
cd game
python main.py
```

Žebříček v prohlížeči: http://127.0.0.1:8000

## Ovládání

| klávesa | co dělá |
|---|---|
| šipky / WASD | pohyb |
| ENTER | start hry (po zadání jména) |
| mezerník | pokračovat po chycení / do dalšího kola |
| L | žebříček (v menu) |
| ESC | zpět do menu / konec |

## Struktura

```
game/
  main.py         hlavní smyčka, kola, HUD, obrazovky
  maze.py         generování bludiště + BFS
  entities.py     hráč, příšerky, předměty a jejich kreslení
  sounds.py       generátor zvuků (vytvoří assets/sfx/*.wav)
  api_client.py   komunikace se serverem + offline záloha
  settings.py     všechna čísla a barvy na jednom místě
server/
  main.py         FastAPI + SQLite
```

## Test bez okna

```bash
cd game
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python main.py --smoke 2000
```
Hra se sama „odehraje“ 2000 snímků – hodí se na kontrolu, že se nic nerozbilo
po tvých úpravách.

## Kde si hrát dál (nápady na učení)

1. **settings.py** – nejjednodušší start: změň barvy, rychlosti, počet životů.
2. **A\* místo BFS** v `maze.py` – porovnej si, kolik buněk každý algoritmus projde.
3. **Nové příšerky** – v `settings.py` do `MONSTERS`, kreslení v `entities.py`.
4. **Chytřejší příšerka** – ať občas hlídá východ místo pronásledování hráče.
5. **Ukládání postupu** – nový endpoint `POST /progress` a tabulka `progress`.
6. **Vlastní grafika** – Pillow nebo hotové PNG přes `pygame.image.load()`.
7. **Nasadit server** na Raspberry Pi doma → žebříček pro celou rodinu.

## Poznámky

- Hra používá jen standardní `urllib`, takže `requests` není potřeba. Kdybys chtěl
  `requests` (jako v tvém návrhu), stačí přepsat `api_client.py`.
- Databáze `scores.db` se vytvoří sama při prvním spuštění serveru.
- Adresu serveru změníš v `game/settings.py` (`API_URL`) – třeba na IP Raspberry Pi.
