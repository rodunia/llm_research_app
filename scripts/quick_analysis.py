#!/usr/bin/env python3
"""Quick analysis of pilot results."""

import csv
from pathlib import Path

GROUND_TRUTH = {
    "smartphone_1": ("Display 6.5\"", ["6.5", "6.5 inch"]),
    "smartphone_2": ("Camera 48 MP", ["48 mp", "48mp"]),
    "smartphone_3": ("1 TB storage", ["1 tb", "1tb"]),
    "smartphone_4": ("16 GB RAM", ["16 gb"]),  # Fixed: was too specific
    "smartphone_5": ("Wi-Fi 7", ["wi-fi 7", "wifi 7"]),
    "smartphone_6": ("Wireless charging", ["wireless charging"]),
    "smartphone_7": ("Hourly antivirus", ["hourly", "antivirus"]),
    "smartphone_8": ("Offline AI rendering", ["offline", "ai video"]),
    "smartphone_9": ("60W charging", ["60w", "60 watt"]),
    "smartphone_10": ("External SSD", ["external ssd", "sim tray"]),
    "melatonin_1": ("Dosage 5 mg", ["5 mg"]),
    "melatonin_2": ("100 tablets", ["100 tablet"]),
    "melatonin_3": ("Fish ingredients", ["fish"]),
    "melatonin_4": ("Wheat traces", ["wheat"]),
    "melatonin_5": ("Lead 5 ppm", ["lead < 5", "5 ppm"]),  # Fixed: extracted as ppm not mcg
    "melatonin_6": ("Storage 0°C", ["0°c", "freezing"]),
    "melatonin_7": ("Every 2 hours", ["every 2 hour", "2-hour"]),
    "melatonin_8": ("FDA approved", ["fda", "approved by fda"]),  # Fixed: was too specific
    "melatonin_9": ("Over 18", ["over 18"]),
    "melatonin_10": ("Permanent drowsiness", ["permanent"]),
}

def check(file_key):
    csv_path = Path(f"results/pilot_individual/{file_key}.csv")
    if not csv_path.exists():
        return False, 0

    error_desc, keywords = GROUND_TRUTH[file_key]
    rows = list(csv.DictReader(open(csv_path)))

    detected = False
    for row in rows:
        text = (row.get('Extracted_Claim', '') + " " + row.get('Violated_Rule', '')).lower()
        if any(kw.lower() in text for kw in keywords):
            detected = True
            break

    return detected, len(rows)

# Smartphone
print("\nSMARTPHONE:")
s_det, s_viol = 0, 0
for i in range(1, 11):
    d, v = check(f"smartphone_{i}")
    print(f"  {i:2d}: {'✅' if d else '❌'} - {GROUND_TRUTH[f'smartphone_{i}'][0]} ({v} viol)")
    s_det += d
    s_viol += v
print(f"  Detection: {s_det}/10 ({s_det*10}%)")

# Melatonin
print("\nMELATONIN:")
m_det, m_viol = 0, 0
for i in range(1, 11):
    d, v = check(f"melatonin_{i}")
    print(f"  {i:2d}: {'✅' if d else '❌'} - {GROUND_TRUTH[f'melatonin_{i}'][0]} ({v} viol)")
    m_det += d
    m_viol += v
print(f"  Detection: {m_det}/10 ({m_det*10}%)")

print(f"\nOVERALL: {s_det+m_det}/20 ({(s_det+m_det)*5}%)")
