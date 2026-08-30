# 🏃 Únik před příšerkou

Bludišťová hra pro děti v Pythonu + Pygame, s leaderboardem na FastAPI + SQLite.

- Bludiště se generuje pokaždé znovu (algoritmus *recursive backtracker*)
- Sbírání mincí a hvězdiček, klíč odemyká východ
- Příšerka hledá cestu pomocí **BFS** – opravdu bludištěm proplouvá za tebou
- Každé kolo: větší bludiště, rychlejší příšerka, víc příšerek (max 4)
- Mód **„světla zhasla“** od 4. kola – vidíš jen kolem sebe
- Bonusy: zrychlení, zmrazení příšerky, neviditelnost
- Ovládání šipkami (nebo WASD), 3 srdíčka, žádné násilí – příšerka tě jen polechtá
- Zvuky si hra vyrobí sama
