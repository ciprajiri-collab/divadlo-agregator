#!/usr/bin/env python3
"""
Agregátor TOP divadelních představení
Scraper i-divadlo.cz → public/data.json

Spouštěn automaticky každou neděli přes GitHub Actions.
Lze spustit ručně: python scraper.py
"""
import json, re, time, random, logging
from datetime import date, datetime
from pathlib import Path
from typing import Optional
import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

BASE_URL        = "https://www.i-divadlo.cz"
OUTPUT          = Path("public/data.json")
CQI_THRESHOLD   = 70.0
MIN_DELAY       = 2.0
MAX_DELAY       = 5.0
TIMEOUT         = 15

HEADERS = {
    "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "cs-CZ,cs;q=0.9",
    "Accept":          "text/html,application/xhtml+xml",
    "Referer":         BASE_URL,
}

# Seznam divadel ke scrapování (slug z URL → metadata)
THEATERS = {
    # Praha
    "narodni-divadlo":          {"name": "Národní divadlo",           "city": "Praha",             "region": "Praha"},
    "dejvicke-divadlo":         {"name": "Dejvické divadlo",          "city": "Praha",             "region": "Praha"},
    "divadlo-na-vinohradech":   {"name": "Divadlo na Vinohradech",    "city": "Praha",             "region": "Praha"},
    "svandovo-divadlo":         {"name": "Švandovo divadlo",          "city": "Praha",             "region": "Praha"},
    "cinoherni-klub":           {"name": "Činoherní klub",            "city": "Praha",             "region": "Praha"},
    "divadlo-na-zabradli":      {"name": "Divadlo Na zábradlí",       "city": "Praha",             "region": "Praha"},
    "divadlo-bez-zabradli":     {"name": "Divadlo Bez zábradlí",      "city": "Praha",             "region": "Praha"},
    "divadlo-pod-palmovkou":    {"name": "Divadlo pod Palmovkou",     "city": "Praha",             "region": "Praha"},
    "divadlo-na-fidlovacce":    {"name": "Divadlo Na Fidlovačce",     "city": "Praha",             "region": "Praha"},
    "divadlo-na-jezerce":       {"name": "Divadlo Na Jezerce",        "city": "Praha",             "region": "Praha"},
    "mestska-divadla-prazska":  {"name": "Městská divadla pražská",   "city": "Praha",             "region": "Praha"},
    "divadelni-spolek-kaspar":  {"name": "Spolek Kašpar",             "city": "Praha",             "region": "Praha"},
    "studio-ypsilon":           {"name": "Studio Ypsilon",            "city": "Praha",             "region": "Praha"},
    "divadlo-komedie":          {"name": "Divadlo Komedie",           "city": "Praha",             "region": "Praha"},
    "divadlo-broadway":         {"name": "Divadlo Broadway",          "city": "Praha",             "region": "Praha"},
    "divadlo-ungelt":           {"name": "Divadlo Ungelt",            "city": "Praha",             "region": "Praha"},
    "hudebni-divadlo-karlin":   {"name": "Hudební divadlo Karlín",    "city": "Praha",             "region": "Praha"},
    "divadlo-na-maninach":      {"name": "Divadlo Na Maninách",       "city": "Praha",             "region": "Praha"},
    "divadlo-hybernia":         {"name": "Divadlo Hybernia",          "city": "Praha",             "region": "Praha"},
    "studio-dva":               {"name": "Studio DVA",                "city": "Praha",             "region": "Praha"},
    # Brno
    "narodni-divadlo-brno":     {"name": "Národní divadlo Brno",      "city": "Brno",              "region": "Jihomoravský kraj"},
    "mestske-divadlo-brno":     {"name": "Městské divadlo Brno",      "city": "Brno",              "region": "Jihomoravský kraj"},
    "divadlo-husa-na-provazku": {"name": "Divadlo Husa na provázku",  "city": "Brno",              "region": "Jihomoravský kraj"},
    "divadlo-bolka-polivky":    {"name": "Divadlo Bolka Polívky",     "city": "Brno",              "region": "Jihomoravský kraj"},
    "hadivadlo":                {"name": "HaDivadlo",                  "city": "Brno",              "region": "Jihomoravský kraj"},
    "divadlo-radost":           {"name": "Divadlo Radost",            "city": "Brno",              "region": "Jihomoravský kraj"},
    # Ostrava
    "narodni-divadlo-moravskoslezske": {"name": "Národní divadlo moravskoslezské", "city": "Ostrava", "region": "Moravskoslezský kraj"},
    "divadlo-petra-bezruce":    {"name": "Divadlo Petra Bezruče",     "city": "Ostrava",           "region": "Moravskoslezský kraj"},
    "komorni-scena-arena":      {"name": "Komorní scéna Aréna",       "city": "Ostrava",           "region": "Moravskoslezský kraj"},
    # Plzeň
    "divadlo-jktyla":           {"name": "Divadlo J. K. Tyla",        "city": "Plzeň",             "region": "Plzeňský kraj"},
    "divadlo-alfa":             {"name": "Divadlo Alfa",              "city": "Plzeň",             "region": "Plzeňský kraj"},
    # Liberec
    "divadlo-f-x-saldy-liberec":{"name": "Divadlo F. X. Šaldy",      "city": "Liberec",           "region": "Liberecký kraj"},
    "naivni-divadlo-liberec":   {"name": "Naivní divadlo Liberec",    "city": "Liberec",           "region": "Liberecký kraj"},
    # Hradec Králové
    "klicperovo-divadlo":       {"name": "Klicperovo divadlo",        "city": "Hradec Králové",    "region": "Královéhradecký kraj"},
    "divadlo-drak":             {"name": "Divadlo Drak",              "city": "Hradec Králové",    "region": "Královéhradecký kraj"},
    # Pardubice
    "vychodoceske-divadlo":     {"name": "Východočeské divadlo",      "city": "Pardubice",         "region": "Pardubický kraj"},
    # Olomouc
    "moravske-divadlo-olomouc": {"name": "Moravské divadlo Olomouc",  "city": "Olomouc",           "region": "Olomoucký kraj"},
    # České Budějovice
    "jihoceske-divadlo":        {"name": "Jihočeské divadlo",         "city": "České Budějovice",  "region": "Jihočeský kraj"},
    # Zlín
    "mestske-divadlo-zlin":     {"name": "Městské divadlo Zlín",      "city": "Zlín",              "region": "Zlínský kraj"},
    "slovacke-divadlo":         {"name": "Slovácké divadlo",          "city": "Uherské Hradiště",  "region": "Zlínský kraj"},
    # Jihlava
    "horacke-divadlo-jihlava":  {"name": "Horácké divadlo Jihlava",   "city": "Jihlava",           "region": "Kraj Vysočina"},
    # Karlovy Vary
    "karlovarske-mestske-divadlo": {"name": "Karlovarské městské divadlo", "city": "Karlovy Vary", "region": "Karlovarský kraj"},
    # Opava / Ústí
    "slezske-divadlo":          {"name": "Slezské divadlo Opava",     "city": "Opava",             "region": "Moravskoslezský kraj"},
    "cinoherni-studio":         {"name": "Činoherní studio",          "city": "Ústí nad Labem",    "region": "Ústecký kraj"},
}


def get(url: str, delay: bool = True) -> Optional[requests.Response]:
    if delay:
        wait = random.uniform(MIN_DELAY, MAX_DELAY)
        logger.debug("Čekám %.1f s...", wait)
        time.sleep(wait)
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        logger.debug("HTTP %d → %s", r.status_code, url)
        return r if r.status_code == 200 else None
    except Exception as e:
        logger.warning("Chyba: %s → %s", url, e)
        return None


def normalize(raw: Optional[str]) -> Optional[float]:
    if not raw:
        return None
    c = raw.strip()
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*%", c)
    if m:
        return min(max(float(m.group(1).replace(",", ".")), 0.0), 100.0)
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*/\s*(\d+(?:[.,]\d+)?)", c)
    if m:
        n, d = float(m.group(1).replace(",", ".")), float(m.group(2).replace(",", "."))
        if d > 0:
            return min(max((n / d) * 100, 0.0), 100.0)
    return None


def cqi(ed: Optional[float], usr: Optional[float]) -> Optional[float]:
    if ed is not None and usr is not None:
        return round(ed * 0.7 + usr * 0.3, 1)
    if usr is not None:
        return round(usr, 1)
    if ed is not None:
        return round(ed, 1)
    return None


def parse_date(raw: str, today: date) -> Optional[str]:
    m = re.match(r"(\d{1,2})\.(\d{1,2})\.*", raw.strip())
    if not m:
        return None
    day, month = int(m.group(1)), int(m.group(2))
    for offset in (0, 1):
        try:
            c = date(today.year + offset, month, day)
            if c >= today:
                return c.isoformat()
        except ValueError:
            continue
    return None


def parse_performance(html: str, url: str, meta: dict) -> Optional[dict]:
    soup  = BeautifulSoup(html, "html.parser")
    today = date.today()

    # Název
    el = soup.select_one("h1[itemprop='name']")
    if not el:
        return None
    title = el.get_text(strip=True)

    # Hodnocení
    cols = soup.select(".hra_hodnoc_prum_sloupec")
    ed_raw = usr_raw = None
    if len(cols) >= 2:
        is_first_editorial = "Redakce" in cols[0].get_text() or "redakce" in cols[0].get_text()
        ed_col, usr_col = (cols[0], cols[1]) if is_first_editorial else (cols[1], cols[0])
        ed_el  = ed_col.select_one(".hra_hodnoc_prum_cislo")
        usr_el = usr_col.select_one(".hra_hodnoc_prum_cislo")
        ed_raw  = ed_el.get_text(strip=True)  if ed_el  else None
        usr_raw = usr_el.get_text(strip=True) if usr_el else None
    elif len(cols) == 1:
        val_el = cols[0].select_one(".hra_hodnoc_prum_cislo")
        raw    = val_el.get_text(strip=True) if val_el else None
        if "Redakce" in cols[0].get_text():
            ed_raw = raw
        else:
            usr_raw = raw

    ed  = normalize(ed_raw)
    usr = normalize(usr_raw)
    score = cqi(ed, usr)

    if score is None or score <= CQI_THRESHOLD:
        return None

    # Termíny (pouze budoucí)
    rows = soup.select(
        ".hra_program.mobile-none tr.hra_program_lichy,"
        ".hra_program.mobile-none tr.hra_program_sudy"
    )
    dates = []
    for row in rows:
        tds     = row.find_all("td")
        date_el = row.find("big")
        time_el = row.find("i")
        raw_d   = date_el.get_text(strip=True) if date_el else ""
        raw_t   = time_el.get_text(strip=True) if time_el else ""
        venue   = tds[4].get_text(strip=True)  if len(tds) > 4 else ""
        iso     = parse_date(raw_d, today)
        if iso:
            dates.append({
                "text": " | ".join(p for p in [raw_d.rstrip("."), raw_t, venue] if p),
                "date": iso,
                "time": raw_t,
            })

    if not dates:
        return None  # Žádné budoucí termíny

    # Počet uživatelských hodnocení
    review_el    = soup.select_one("span[itemprop='reviewCount']")
    review_count = int(review_el.get_text(strip=True)) if review_el else 0

    return {
        "title":              title,
        "theater_name":       meta["name"],
        "city":               meta["city"],
        "region":             meta["region"],
        "source_url":         url,
        "editorial_rating":   ed,
        "user_rating":        usr,
        "cqi":                score,
        "review_count":       review_count,
        "is_critic_verified": ed is not None,
        "rating_confidence":  "full" if (ed and usr) else ("user_only" if usr else "editorial_only"),
        "dates":              sorted(dates, key=lambda d: d["date"]),
        "scraped_at":         datetime.utcnow().isoformat(),
    }


def get_links(slug: str) -> list[str]:
    r = get(f"{BASE_URL}/divadlo/{slug}")
    if not r:
        return []
    soup = BeautifulSoup(r.text, "html.parser")
    links, seen = [], set()
    for a in soup.find_all("a", href=True):
        href  = a["href"]
        parts = [p for p in href.split("/") if p]
        if (len(parts) == 3 and parts[0] == "divadlo"
                and parts[1] == slug
                and "?" not in href and "#" not in href):
            full = f"{BASE_URL}{href}" if not href.startswith("http") else href
            if full not in seen:
                seen.add(full)
                links.append(full)
    return links


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    results = []

    for i, (slug, meta) in enumerate(THEATERS.items(), 1):
        logger.info("── Divadlo %d/%d: %s", i, len(THEATERS), meta["name"])
        links = get_links(slug)
        if not links:
            continue

        for j, url in enumerate(links, 1):
            logger.info("   Inscenace %d/%d: %s", j, len(links), url.split("/")[-1])
            r = get(url)
            if not r:
                continue
            perf = parse_performance(r.text, url, meta)
            if perf:
                results.append(perf)
                logger.info("   ✓ %s | CQI %.1f | %d termínů", perf["title"], perf["cqi"], len(perf["dates"]))

    results.sort(key=lambda p: p["cqi"], reverse=True)

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump({"updated_at": datetime.utcnow().isoformat(),
                   "total": len(results), "performances": results},
                  f, ensure_ascii=False, indent=2)

    logger.info("═══════════════════════════════════════════════")
    logger.info("HOTOVO: %d představení uloženo → %s", len(results), OUTPUT)
    logger.info("═══════════════════════════════════════════════")


if __name__ == "__main__":
    main()
