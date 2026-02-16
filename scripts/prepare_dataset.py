from __future__ import annotations
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]   # .../scripts/.. = root projekta
RAW_BASE = PROJECT_ROOT / "data" / "raw"
OUT_DIR = PROJECT_ROOT / "data" / "processed"
OUT_DIR.mkdir(parents=True, exist_ok=True)

FILES = ["datatraining.txt", "datatest.txt", "datatest2.txt"]

def find_raw_dir() -> Path:
    matches = list(RAW_BASE.rglob("datatraining.txt"))
    if not matches:
        raise FileNotFoundError(
            f"Ne mogu da nađem datatraining.txt ispod {RAW_BASE}. "
            "Proveri da li su fajlovi zaista u data/raw."
        )
    return matches[0].parent

RAW_DIR = find_raw_dir()


FILES = ["datatraining.txt", "datatest.txt", "datatest2.txt"]

def load_one(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)  # radi za UCI occupancy fajlove (CSV-like) :contentReference[oaicite:7]{index=7}
    # Normalizacija naziva kolona
    df.columns = [c.strip() for c in df.columns]
    # Parse timestamp
    df["date"] = pd.to_datetime(df["date"], errors="raise")
    return df

def main() -> None:
    frames = []
    for name in FILES:
        p = RAW_DIR / name
        if not p.exists():
            raise FileNotFoundError(f"Missing file: {p}")
        df = load_one(p)
        df["source_file"] = name
        frames.append(df)

    all_df = pd.concat(frames, ignore_index=True)

    # UCI dataset je bez missing vrednosti :contentReference[oaicite:8]{index=8}
    # ali uklanjamo duplikate (ne smeta, plus je “production-like”)
    all_df = all_df.drop_duplicates()

    # Kanonska imena (što ćemo koristiti u API-ju)
    all_df = all_df.rename(columns={
        "date": "ts",
        "Temperature": "temperature_c",
        "Humidity": "humidity_percent",
        "Light": "light_lux",
        "CO2": "co2_ppm",
        "HumidityRatio": "humidity_ratio",
        "Occupancy": "occupancy",
        "id": "source_id"
    })

    # occupancy u bool
    all_df["occupancy"] = all_df["occupancy"].astype(int).astype(bool)

    out = OUT_DIR / "occupancy_readings.csv"
    all_df.to_csv(out, index=False)
    print(f"Wrote: {out} (rows={len(all_df)})")

if __name__ == "__main__":
    main()