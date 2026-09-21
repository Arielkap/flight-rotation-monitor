# ✈️ Flight & Offshore Rotation Monitor

Automatyczny system śledzenia grafiku rotacji offshore oraz cen biletów lotniczych dla kluczowych połączeń domowych i urlopowych.

---

## 🎯 Przeznaczenie i Funkcje

1. **Kalkulator Cykli Rotacji (`calculate_shifts.py`):**
   * Wylicza dokładne daty powrotów i wolnego w domu na podstawie 28-dniowego cyklu rotacyjnego.
   * Automatycznie generuje terminy urlopów na kolejne cykle w przód.

2. **Skaner Cen Lotów (`flight_checker_engine.py`):**
   * Śledzi ceny połączeń lotniczych na kluczowych trasach:
     * **Aberdeen (ABZ) ➔ Gdańsk (GDN)** — trasa rotacyjna (próg alertu: £35).
     * **Edynburg (EDI) ➔ Antalya (AYT)** — trasa urlopowa (próg alertu: £120).
     * **KLM Hub (AMS)** — loty przesiadkowe z Aberdeen przez Amsterdam.
   * Współpracuje z harmonogramem cron i powiadomieniami Mando na Telegramie.

---

## 🚀 Uruchomienie

### Sprawdzenie terminów rotacji:
```bash
python3 calculate_shifts.py
```

### Sprawdzenie statusu cen lotów:
```bash
python3 check_flights.py
```
