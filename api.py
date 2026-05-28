"""
o‘zbekiston hududlari — viloyat, tuman, MFY
Manba: https://openbudget.uz/api/v1

Ishlatish:
    pip install requests
    python fetch_hududlar.py

Natija: data_hududlar/
    ├── regions.json
    ├── districts.json
    ├── mfy.json
    └── <Viloyat nomi>/
        └── <Tuman nomi>.json
"""

import json
import os
import re
import time

import requests

BASE = "https://openbudget.uz/api/v1"
HEADERS = {"Accept": "application/json", "User-Agent": "Mozilla/5.0"}
OUTPUT = "data_hududlar"

# ─────────────────────────────────────────
# Kiril → Lotin
# ─────────────────────────────────────────
KIRIL_LOTIN = {
    "А": "A",  "а": "a",  "Б": "B",  "б": "b",
    "В": "V",  "в": "v",  "Г": "G",  "г": "g",
    "Д": "D",  "д": "d",  "Е": "E",  "е": "e",
    "Ё": "Yo", "ё": "yo", "Ж": "J",  "ж": "j",
    "З": "Z",  "з": "z",  "И": "I",  "и": "i",
    "Й": "Y",  "й": "y",  "К": "K",  "к": "k",
    "Л": "L",  "л": "l",  "М": "M",  "м": "m",
    "Н": "N",  "н": "n",  "О": "O",  "о": "o",
    "П": "P",  "п": "p",  "Р": "R",  "р": "r",
    "С": "S",  "с": "s",  "Т": "T",  "т": "t",
    "У": "U",  "у": "u",  "Ф": "F",  "ф": "f",
    "Х": "X",  "х": "x",  "Ц": "Ts", "ц": "ts",
    "Ч": "Ch", "ч": "ch", "Ш": "Sh", "ш": "sh",
    "Щ": "Sh", "щ": "sh", "Ъ": "'",  "ъ": "'",
    "Ы": "I",  "ы": "i",  "Ь": "'",  "ь": "'",
    "Э": "E",  "э": "e",  "Ю": "Yu", "ю": "yu",
    "Я": "Ya", "я": "ya",
    # o‘zbek maxsus
    "Ў": "o‘", "ў": "o‘", "Қ": "Q",  "қ": "q",
    "Ғ": "g‘", "ғ": "g‘", "Ҳ": "H",  "ҳ": "h",
    "Ҷ": "J",  "ҷ": "j",  "Ҝ": "G",  "ҝ": "g",
}


def kiril2lotin(text: str) -> str:
    return "".join(KIRIL_LOTIN.get(ch, ch) for ch in text)


def safe_name(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "_", name).strip()


def fetch(url: str, retries: int = 3) -> dict:
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            if attempt < retries - 1:
                print(f"    ⚠ Xato ({attempt+1}/{retries}): {e} — qayta urinilmoqda...")
                time.sleep(2)
            else:
                raise


def main():
    os.makedirs(OUTPUT, exist_ok=True)

    # ── 1. VILOYATLAR ──────────────────────────────────────
    print("Viloyatlar yuklanmoqda...")
    data = fetch(f"{BASE}/regions")

    regions = []
    for r in data["regions"]:
        regions.append({
            "id":   r["id"],
            "name": kiril2lotin(r["title"]),   # register.py: 'name'
        })
    regions.sort(key=lambda x: x["name"])

    with open(f"{OUTPUT}/regions.json", "w", encoding="utf-8") as f:
        json.dump(regions, f, ensure_ascii=False, indent=2)
    print(f"  ✓ regions.json — {len(regions)} ta viloyat\n")

    # ── 2. TUMANLAR ────────────────────────────────────────
    print("Tumanlar yuklanmoqda...")
    all_districts = []

    for region in regions:
        data = fetch(f"{BASE}/districts?region_id={region['id']}")
        for d in data["districts"]:
            all_districts.append({
                "id":        d["id"],
                "region_id": region["id"],
                "name":      kiril2lotin(d["title"]),  # register.py: 'name'
            })
        print(f"  {region['name']:<35} {data['count']} ta tuman")
        time.sleep(0.1)

    all_districts.sort(key=lambda x: (x["region_id"], x["name"]))

    with open(f"{OUTPUT}/districts.json", "w", encoding="utf-8") as f:
        json.dump(all_districts, f, ensure_ascii=False, indent=2)
    print(f"\n  ✓ districts.json — {len(all_districts)} ta tuman\n")

    # ── 3. MFY LAR ─────────────────────────────────────────
    print("MFY lar yuklanmoqda...")
    all_mfy = []
    total = len(all_districts)

    for i, district in enumerate(all_districts, 1):
        data = fetch(f"{BASE}/quarters?district_id={district['id']}")
        quarters = []

        for q in data["quarters"]:
            name_lotin = kiril2lotin(q["title"])
            entry = {
                "id":          q["id"],
                "district_id": district["id"],
                "region_id":   district["region_id"],
                "name":        name_lotin,            # register.py: 'name'
                "mfy_name":    name_lotin + " MFY",   # villages_keyboard da ishlatiladi
            }
            quarters.append(entry)
            all_mfy.append(entry)

        # Har bir tuman uchun alohida fayl (viloyat papkasida)
        region_name = next(r["name"] for r in regions if r["id"] == district["region_id"])
        region_dir = os.path.join(OUTPUT, safe_name(region_name))
        os.makedirs(region_dir, exist_ok=True)

        with open(
            os.path.join(region_dir, safe_name(district["name"]) + ".json"),
            "w", encoding="utf-8"
        ) as f:
            json.dump(quarters, f, ensure_ascii=False, indent=2)

        # Progress bar
        bar = "█" * int(i / total * 25) + "░" * (25 - int(i / total * 25))
        print(f"\r  [{bar}] {i:>3}/{total}  {district['name']:<30} {len(quarters)} MFY", end="", flush=True)
        time.sleep(0.1)

    print()

    all_mfy.sort(key=lambda x: (x["region_id"], x["district_id"], x["name"]))

    with open(f"{OUTPUT}/mfy.json", "w", encoding="utf-8") as f:
        json.dump(all_mfy, f, ensure_ascii=False, indent=2)

    # ── YAKUNIY HISOBOT ────────────────────────────────────
    print(f"\n{'='*52}")
    print(f"  ✅ TAYYOR")
    print(f"{'='*52}")
    print(f"  regions.json   : {len(regions):>5} ta viloyat")
    print(f"  districts.json : {len(all_districts):>5} ta tuman")
    print(f"  mfy.json       : {len(all_mfy):>5} ta MFY")
    print(f"\n  JSON maydon nomlari (register.py ga mos):")
    print(f"  regions.json   → id, name")
    print(f"  districts.json → id, region_id, name")
    print(f"  mfy.json       → id, district_id, region_id, name, mfy_name")
    print(f"\n  Keyingi qadam:")
    print(f"  cp -r {OUTPUT}/regions.json   app/data/")
    print(f"  cp -r {OUTPUT}/districts.json app/data/")
    print(f"  cp -r {OUTPUT}/mfy.json       app/data/villages.json")
    print(f"{'='*52}")


if __name__ == "__main__":
    main()