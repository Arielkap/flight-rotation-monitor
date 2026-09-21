from datetime import datetime, timedelta

def generate_shift_schedule(start_home_date, cycles=3):
    # Schemat:
    # - 11 października przylot do domu (początek wolnego)
    # - 7 dni wolnego (od 11 do 17 włącznie, powiedzmy praca od 18 lub wylot 19)
    # - Cykl powtarza się co 28 dni (rotacja np. 14/14 lub 21/7, ale tu masz sztywny cykl 28-dniowy).
    
    schedule = []
    current_home = start_home_date
    
    for _ in range(cycles):
        # 7 dni wolnego w domu
        holiday_start = current_home
        holiday_end = current_home + timedelta(days=6)
        schedule.append((holiday_start, holiday_end))
        
        # Kolejny cykl za 28 dni
        current_home += timedelta(days=28)
        
    return schedule

if __name__ == "__main__":
    first_holiday = datetime(2026, 10, 11)
    shifts = generate_shift_schedule(first_holiday)
    for s in shifts:
        print(f"Wolne w domu: {s[0].strftime('%d.%m.%Y')} - {s[1].strftime('%d.%m.%Y')}")
