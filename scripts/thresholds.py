import csv

path = r"G:\IOT I\data\processed\occupancy_readings.csv"

keys = ["temperature_c", "co2_ppm", "humidity_percent", "light_lux"]
cols = {k: [] for k in keys}

with open(path, newline="", encoding="utf-8") as f:
    r = csv.DictReader(f)
    for row in r:
        for k in keys:
            cols[k].append(float(row[k]))

def q(vals, p):
    s = sorted(vals)
    i = int(p * (len(s) - 1))
    return s[i]

for k,v in cols.items():
    print(k, "min", min(v), "p95", q(v, 0.95), "max", max(v), "p05", q(v, 0.05))