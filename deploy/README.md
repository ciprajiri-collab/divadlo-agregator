# Agregátor TOP divadelních představení

Webová aplikace zobrazující nejlepší divadelní představení z i-divadlo.cz,
seřazená podle kompozitního skóre kvality (CQI).

## Jak to funguje

1. Každou neděli ve 3:00 se automaticky spustí scraper
2. Scraper projde ~40 divadel na i-divadlo.cz a stáhne hodnocení
3. Vypočítá CQI = (redakce × 70 %) + (diváci × 30 %)
4. Zobrazí jen představení s CQI > 70 a budoucím termínem
5. Výsledky uloží do `public/data.json`
6. Netlify automaticky nasadí aktualizovanou verzi webu

## Nastavení (jednorázové)

### 1. GitHub
- Nahraj tento ZIP jako nový repozitář na github.com
- Settings → Actions → General → Workflow permissions → Read and write

### 2. Netlify
- New site → Import from GitHub → vyber repozitář
- Build settings se nastaví automaticky z netlify.toml

### 3. První scraping
- Na GitHubu: Actions → Týdenní scraping divadel → Run workflow

## Soubory

- `scraper.py` – Python scraper (stahuje data z i-divadlo.cz)
- `public/index.html` – webová stránka (frontend)
- `public/data.json` – data generovaná scraperem
- `.github/workflows/scrape.yml` – automatické spouštění každou neděli
- `netlify.toml` – konfigurace pro Netlify
