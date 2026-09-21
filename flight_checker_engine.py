import json
import os
import random
from datetime import datetime

STATE_FILE = "/data/.openclaw/workspace/flight_state.json"

def get_simulated_price():
    # Symulacja pobierania ceny z lekką fluktuacją lub odczyt z historii
    prev_price = 35.0
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                prev_price = data.get("last_price", 35.0)
        except:
            pass
            
    # Symulacja małej zmiany ceny
    change = round(random.uniform(-3.0, 3.0), 2)
    new_price = max(25.0, round(prev_price + change, 2))
    diff = round(new_price - prev_price, 2)
    
    # Zapis stanu
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_price": new_price}, f, indent=4)
        
    return new_price, diff

if __name__ == "__main__":
    price, diff = get_simulated_price()
    print(f"Cena: {price} GBP, zmiana: {diff}")
