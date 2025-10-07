#!/usr/bin/env python3
import requests
import csv
import os
from datetime import datetime
from urllib.parse import quote_plus

TARGET_URL = "https://www.sampath.lk/api/exchange-rates"
CSV_PATH = "latest_rates.csv"
MAX_ROWS = 100  # keep latest 100 entries (not counting header)

def fetch_json(scraper_key=None):
    headers = {
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36",
        "Referer": "https://www.sampath.lk/",
        "Origin": "https://www.sampath.lk"
    }

    try:
        r = requests.get(TARGET_URL, headers=headers, timeout=15)
        if r.status_code == 200:
            return r.json()
        else:
            print(f"Primary fetch failed: HTTP {r.status_code}")
    except Exception as e:
        print("Primary fetch error:", e)

    # If primary fail and scraper key present, try ScraperAPI fallback
    if scraper_key:
        try:
            proxy = f"https://api.scraperapi.com/?api_key={scraper_key}&url={quote_plus(TARGET_URL)}"
            r2 = requests.get(proxy, timeout=30)
            if r2.status_code == 200:
                return r2.json()
            else:
                print(f"ScraperAPI fetch failed: HTTP {r2.status_code}")
        except Exception as e:
            print("ScraperAPI error:", e)

    return None

def extract_rates(data):
    if not data or not data.get("success"):
        return None
    currencies = data.get("data", [])
    usd = next((c for c in currencies if c.get("CurrCode") == "USD"), None)
    gbp = next((c for c in currencies if c.get("CurrCode") == "GBP"), None)
    if not usd or not gbp:
        return None
    try:
        usd_rate = float(usd.get("TTBUY"))
        gbp_rate = float(gbp.get("TTBUY"))
    except Exception:
        return None
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return [timestamp, usd_rate, gbp_rate]

def read_existing():
    if not os.path.exists(CSV_PATH):
        return [["Timestamp","USD","GBP"]]
    with open(CSV_PATH, "r", newline="") as f:
        reader = list(csv.reader(f))
        if not reader:
            return [["Timestamp","USD","GBP"]]
        # ensure header present
        if reader[0] != ["Timestamp","USD","GBP"]:
            reader.insert(0, ["Timestamp","USD","GBP"])
        return reader

def write_csv(rows):
    with open(CSV_PATH, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

def main():
    scraper_key = os.environ.get("SCRAPERAPI_KEY")  # optional
    data = fetch_json(scraper_key=scraper_key)
    row = extract_rates(data)
    if not row:
        print("Failed to fetch/parse rates.")
        return 1

    rows = read_existing()
    # insert after header
    rows.insert(1, [row[0], f"{row[1]:.4f}", f"{row[2]:.4f}"])
    # trim to header + MAX_ROWS
    rows = rows[: (1 + MAX_ROWS) ]
    write_csv(rows)
    print(f"✅ Wrote new row: {row}")
    return 0

if __name__ == "__main__":
    import sys
    status = main()
    sys.exit(status)
