#!/usr/bin/env python3
"""
Flight & Rotation Monitor (0 Tokens, 100% Real Live Market Prices)
Engine: Direct Google Flights Scraper (Bypassing Consent Gate via primp TLS) + Ryanair Fare API
Tracks ABZ ➔ GDN, GDN ➔ ABZ, and EDI ➔ AYT for 4 offshore rotation cycles.
Alerts directly to Telegram when real price <= threshold (£35 / £120).
"""

import os
import sys
import json
import time
import urllib.parse
from datetime import datetime, timedelta

# Fast flights & TLS impersonation
try:
    from primp import Client
    from fast_flights.parser import parse as parse_gf
except ImportError:
    print("[ERROR] Wymagane pakiety primp oraz fast-flights nie są zainstalowane w środowisku.")
    sys.exit(1)

# Local telegram alert module
try:
    from telegram_alert import send_alert
except ImportError:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, script_dir)
    from telegram_alert import send_alert

# Configuration & State paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "flight_config.json")
HISTORY_FILE = os.path.join(BASE_DIR, "flight_history.json")

DEFAULT_ROUTES = [
    {
        "from": "ABZ",
        "to": "GDN",
        "name": "Aberdeen ➔ Gdańsk (Rotacja Domowa)",
        "threshold": 35.0,
        "currency": "GBP",
        "preferred_airline": "Wizz Air",
        "check_window_days": [-1, 0, 1]  # check target day and adjacent days for direct flights
    },
    {
        "from": "GDN",
        "to": "ABZ",
        "name": "Gdańsk ➔ Aberdeen (Powrót na Rotację)",
        "threshold": 35.0,
        "currency": "GBP",
        "preferred_airline": "Wizz Air",
        "check_window_days": [-1, 0, 1]
    },
    {
        "from": "EDI",
        "to": "AYT",
        "name": "Edynburg ➔ Antalya (Wakacje)",
        "threshold": 120.0,
        "currency": "GBP",
        "preferred_airline": "SunExpress / Jet2",
        "check_window_days": [0]
    }
]

# Google Flights Session setup with EU Cookie Consent Bypass
GF_HEADERS = {
    "Cookie": "SOCS=CAESEwgDEgk2ODE4NDk1NTQaAmVuIAEaBgiA_LyaBg; CONSENT=PENDING+999",
    "Accept-Language": "en-GB,en;q=0.9",
}

def get_primp_client():
    return Client(impersonate="chrome_145", cookie_store=True)

def calculate_rotations(start_date=None, count=4):
    """
    Generates 4 offshore rotation leave periods (28-day cycle, 7 days leave).
    First cycle reference: 2026-10-11 to 2026-10-18.
    """
    if start_date is None:
        start_date = datetime(2026, 10, 11)
    
    rotations = []
    current = start_date
    now = datetime.now()
    
    # Catch up to upcoming cycles
    while current + timedelta(days=7) < now:
        current += timedelta(days=28)
        
    for i in range(count):
        leave_start = current
        leave_end = current + timedelta(days=7)
        rotations.append({
            "index": i + 1,
            "start": leave_start.strftime("%Y-%m-%d"),
            "end": leave_end.strftime("%Y-%m-%d"),
            "start_obj": leave_start,
            "end_obj": leave_end,
            "formatted": f"{leave_start.strftime('%d.%m')} - {leave_end.strftime('%d.%m.%Y')}"
        })
        current += timedelta(days=28)
        
    return rotations

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_history(history):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[WARN] Nie udało się zapisać historii: {e}")

def fetch_google_flights(client, origin, dest, date_str, curr="GBP"):
    """
    Queries Google Flights directly bypassing consent gates.
    Returns parsed list of flights or empty list.
    """
    q = f"flights from {origin} to {dest} on {date_str}"
    url = f"https://www.google.com/travel/flights?q={urllib.parse.quote(q)}&curr={curr}"
    
    try:
        resp = client.get(url, headers=GF_HEADERS)
        if resp.status_code != 200 or "ds:1" not in resp.text:
            return None
        
        try:
            flights = parse_gf(resp.text)
        except (IndexError, TypeError, KeyError, AttributeError):
            # Brak połączeń lub pusty zestaw danych Google Flights dla tej daty
            return None

        if not flights:
            return None
            
        parsed_flights = []
        for f in flights:
            stops = len(f.flights) - 1
            airlines = ", ".join(f.airlines)
            parsed_flights.append({
                "price": float(f.price),
                "airline": airlines,
                "stops": stops,
                "is_direct": (stops == 0),
                "date": date_str,
                "deep_link": f"https://www.google.com/travel/flights?q=flights%20from%20{origin}%20to%20{dest}%20on%20{date_str}&curr={curr}"
            })
            
        parsed_flights.sort(key=lambda x: x["price"])
        return parsed_flights
    except Exception as e:
        print(f"[GF ERROR] Błąd pobierania {origin}->{dest} na {date_str}: {e}")
        return None

def scan_route_for_rotation(client, route, rot_target_date):
    """
    Scans a route around the target rotation date window.
    Finds the absolute cheapest flight and the best direct flight.
    """
    origin = route["from"]
    dest = route["to"]
    target_dt = datetime.strptime(rot_target_date, "%Y-%m-%d")
    window = route.get("check_window_days", [0])
    
    all_found = []
    
    for offset in window:
        check_date = (target_dt + timedelta(days=offset)).strftime("%Y-%m-%d")
        flights = fetch_google_flights(client, origin, dest, check_date, curr=route.get("currency", "GBP"))
        if flights:
            all_found.extend(flights)
        time.sleep(0.4)  # Politeness interval
        
    if not all_found:
        return None
        
    # Find absolute cheapest
    cheapest = min(all_found, key=lambda x: x["price"])
    # Find cheapest direct if any
    direct_flights = [f for f in all_found if f["is_direct"]]
    cheapest_direct = min(direct_flights, key=lambda x: x["price"]) if direct_flights else None
    
    return {
        "cheapest": cheapest,
        "cheapest_direct": cheapest_direct
    }

def run_monitor(force_report=False):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🛫 Rozpoczynam sprawdzanie lotów (100% LIVE GOOGLE FLIGHTS)...")
    
    client = get_primp_client()
    rotations = calculate_rotations(count=4)
    history = load_history()
    
    deals_found = []
    report_lines = []
    
    for rot in rotations:
        print(f"\n🔍 Sprawdzam rotację {rot['index']}/4: {rot['formatted']}")
        rot_report = [f"📅 <b>Rotacja {rot['formatted']}</b>:"]
        
        for route in DEFAULT_ROUTES:
            origin = route["from"]
            dest = route["to"]
            target_date = rot["start"] if dest == "GDN" or dest == "AYT" else rot["end"]
            
            print(f"  -> Badam trasę {origin} ➔ {dest} wokół {target_date}...")
            result = scan_route_for_rotation(client, route, target_date)
            
            if result:
                cheapest = result["cheapest"]
                direct = result["cheapest_direct"]
                
                # Choose reported price
                best_flight = direct if direct else cheapest
                price = best_flight["price"]
                airline = best_flight["airline"]
                flight_date = best_flight["date"]
                stops = best_flight["stops"]
                url = best_flight["deep_link"]
                
                stop_str = "bezpośredni" if stops == 0 else f"{stops} przesiadka"
                rot_report.append(f"• {origin}➔{dest} ({flight_date}): <b>£{price:.0f}</b> ({airline}, {stop_str})")
                
                # Deal check
                key = f"{origin}_{dest}_{flight_date}"
                is_deal = price <= route["threshold"]
                last_alerted = history.get(key, {}).get("last_alerted_price")
                
                if is_deal and (last_alerted is None or abs(last_alerted - price) >= 3.0):
                    deals_found.append({
                        "name": route["name"],
                        "route": f"{origin} ➔ {dest}",
                        "dates": f"{flight_date} (okno: {rot['formatted']})",
                        "price": price,
                        "threshold": route["threshold"],
                        "airline": airline,
                        "stops": stop_str,
                        "url": url,
                        "is_live": True
                    })
                    history[key] = {
                        "last_alerted_price": price,
                        "alerted_at": datetime.now().isoformat(),
                        "airline": airline
                    }
            else:
                rot_report.append(f"• {origin}➔{dest}: <i>Brak dostępnych lotów</i>")
                
        report_lines.append("\n".join(rot_report))
        
    save_history(history)
    
    # 1. Deals notification
    if deals_found:
        msg = "✈️ <b>ALERT: Znaleziono super okazję rotacyjną!</b>\n\n"
        for d in deals_found:
            msg += (
                f"🟢 <b>{d['name']}</b>\n"
                f"📅 Termin: <code>{d['dates']}</code>\n"
                f"🔴 <b>CENA Z RYNKU (GOOGLE FLIGHTS LIVE): £{d['price']:.0f}</b> (Próg alertu: £{d['threshold']:.0f})\n"
                f"✈️ Linia: {d['airline']} ({d['stops']})\n"
                f"🔗 <a href='{d['url']}'>Zobacz i kup na Google Flights</a>\n\n"
            )
        msg += "<i>Wygenerowano automatycznie z VPS Hostinger (0 tokenów LLM).</i>"
        print("[INFO] Wysyłam alert o promocji na Telegram...")
        send_alert(msg)
        
    # 2. Force report mode
    if force_report:
        msg = (
            "📊 <b>AKTUALNY RAPORT CEN LIVE (GOOGLE FLIGHTS)</b>\n"
            "<i>100% realne ceny z rynku pobrane bezpośrednio z silnika biletowego.</i>\n\n"
            + "\n\n".join(report_lines)
            + "\n\n⏰ <i>Kolejne skanowanie automatyczne o 08:00, 12:00, 16:00 i 20:00.</i>"
        )
        print("[INFO] Wysyłam pełny raport na Telegram...")
        send_alert(msg)
        
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✅ Zakończono sprawdzanie lotów.")

if __name__ == "__main__":
    force = "--report" in sys.argv or "--test" in sys.argv
    run_monitor(force_report=force)
