import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score, confusion_matrix, classification_report


FEATURE_COLS = ["temperature_c", "humidity_percent", "light_lux", "co2_ppm"]

# Ovo mora da match-uje MLaaS /predict input (schemas.py)
MODEL_FEATURE_NAMES = [
    "temp_mean", "temp_std",
    "hum_mean", "hum_std",
    "light_mean", "light_std",
    "co2_mean", "co2_std",
    "temp_last", "hum_last", "light_last", "co2_last",
]

@dataclass
class SplitConfig:
    train_frac: float = 0.70
    val_frac: float = 0.15
    # test_frac = 1 - train - val

def iso_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

def coerce_bool_series(s: pd.Series) -> pd.Series:
    # podržava: True/False, 0/1, "true"/"false"
    if s.dtype == bool:
        return s.astype(int)
    if np.issubdtype(s.dtype, np.number):
        return (s.astype(float) != 0).astype(int)
    return s.astype(str).str.strip().str.lower().isin(["1", "true", "yes", "y", "t"]).astype(int)

def load_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)

    # TS kolona: podrži "ts" ili "date"
    if "ts" not in df.columns and "date" in df.columns:
        df = df.rename(columns={"date": "ts"})
    if "ts" not in df.columns:
        raise ValueError("CSV mora da ima kolonu 'ts' ili 'date'")

    # source_id opcionalan
    if "source_id" not in df.columns:
        df["source_id"] = 1

    # label mora da postoji
    if "occupancy" not in df.columns:
        raise ValueError("CSV mora da ima kolonu 'occupancy' (label)")

    # parse vremena
    df["ts"] = pd.to_datetime(df["ts"], utc=True, errors="coerce")
    df = df.dropna(subset=["ts"])

    # numeric kolone
    for c in FEATURE_COLS:
        if c not in df.columns:
            raise ValueError(f"CSV nema kolonu '{c}'")
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # label u 0/1
    df["occupancy"] = coerce_bool_series(df["occupancy"])

    # sort po source i vremenu
    df = df.sort_values(["source_id", "ts"]).reset_index(drop=True)

    # izbaci redove gde su feature-i NaN
    df = df.dropna(subset=FEATURE_COLS)

    return df

def build_window_features(df: pd.DataFrame, window: int) -> pd.DataFrame:
    """
    Pravi window feature-e po source_id:
    - mean/std po prozoru (window) za temp/hum/light/co2
    - last vrednost (trenutni red)
    """
    if window < 2:
        raise ValueError("window mora biti >= 2")

    g = df.groupby("source_id", group_keys=False)

    out = df[["source_id", "ts"]].copy()

    # rolling mean/std (ddof=0 = population std, konzistentno sa pstdev)
    out["temp_mean"] = g["temperature_c"].rolling(window).mean().reset_index(level=0, drop=True)
    out["temp_std"]  = g["temperature_c"].rolling(window).std(ddof=0).reset_index(level=0, drop=True)

    out["hum_mean"]  = g["humidity_percent"].rolling(window).mean().reset_index(level=0, drop=True)
    out["hum_std"]   = g["humidity_percent"].rolling(window).std(ddof=0).reset_index(level=0, drop=True)

    out["light_mean"] = g["light_lux"].rolling(window).mean().reset_index(level=0, drop=True)
    out["light_std"]  = g["light_lux"].rolling(window).std(ddof=0).reset_index(level=0, drop=True)

    out["co2_mean"]  = g["co2_ppm"].rolling(window).mean().reset_index(level=0, drop=True)
    out["co2_std"]   = g["co2_ppm"].rolling(window).std(ddof=0).reset_index(level=0, drop=True)

    # last (= trenutni red)
    out["temp_last"]  = df["temperature_c"].astype(float)
    out["hum_last"]   = df["humidity_percent"].astype(float)
    out["light_last"] = df["light_lux"].astype(float)
    out["co2_last"]   = df["co2_ppm"].astype(float)

    out["y"] = df["occupancy"].astype(int)

    # prvih window-1 redova po source_id nemaju rolling -> NaN
    out = out.dropna(subset=MODEL_FEATURE_NAMES).reset_index(drop=True)

    # obavezno sortiraj globalno po vremenu za time split
    out = out.sort_values("ts").reset_index(drop=True)
    return out

def time_split(df_feat: pd.DataFrame, cfg: SplitConfig):
    n = len(df_feat)
    if n < 100:
        print(f"[warn] malo uzoraka ({n}). Radiće, ali metrike nisu stabilne.")

    train_end = int(n * cfg.train_frac)
    val_end = int(n * (cfg.train_frac + cfg.val_frac))

    train = df_feat.iloc[:train_end]
    val = df_feat.iloc[train_end:val_end]
    test = df_feat.iloc[val_end:]

    return train, val, test

def eval_split(name: str, y_true, y_prob):
    y_pred = (y_prob >= 0.5).astype(int)
    acc = accuracy_score(y_true, y_pred)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    try:
        auc = roc_auc_score(y_true, y_prob)
    except Exception:
        auc = float("nan")

    cm = confusion_matrix(y_true, y_pred)

    print(f"\n=== {name} ===")
    print(f"accuracy: {acc:.4f}")
    print(f"f1:       {f1:.4f}")
    print(f"roc_auc:  {auc:.4f}")
    print("confusion_matrix [ [tn fp] [fn tp] ]:")
    print(cm)
    return {"accuracy": acc, "f1": f1, "roc_auc": auc, "cm": cm.tolist()}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="../data/processed/occupancy_readings.csv", help="putanja do CSV-a")
    ap.add_argument("--window", type=int, default=20, help="veličina sliding window-a (N)")
    ap.add_argument("--out", default="model.joblib", help="gde snimiti model")
    ap.add_argument("--meta", default="model.meta.json", help="gde snimiti metapodatke")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    np.random.seed(args.seed)

    data_path = Path(args.data).resolve()
    if not data_path.exists():
        raise FileNotFoundError(f"Ne postoji CSV: {data_path}")

    print(f"[train] reading: {data_path}")
    df = load_csv(data_path)
    print(f"[train] rows after cleanup: {len(df)}")

    df_feat = build_window_features(df, window=args.window)
    print(f"[train] rows with window features (window={args.window}): {len(df_feat)}")

    train_df, val_df, test_df = time_split(df_feat, SplitConfig())

    X_train = train_df[MODEL_FEATURE_NAMES].to_numpy(dtype=float)
    y_train = train_df["y"].to_numpy(dtype=int)

    X_val = val_df[MODEL_FEATURE_NAMES].to_numpy(dtype=float)
    y_val = val_df["y"].to_numpy(dtype=int)

    X_test = test_df[MODEL_FEATURE_NAMES].to_numpy(dtype=float)
    y_test = test_df["y"].to_numpy(dtype=int)

    print(f"[train] split sizes: train={len(train_df)}, val={len(val_df)}, test={len(test_df)}")

    # Baseline model: LogisticRegression + standardizacija
    model = Pipeline(steps=[
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=args.seed)),
    ])

    model.fit(X_train, y_train)

    # Probabilities
    val_prob = model.predict_proba(X_val)[:, 1] if len(X_val) else np.array([])
    test_prob = model.predict_proba(X_test)[:, 1] if len(X_test) else np.array([])

    metrics = {}
    if len(X_val):
        metrics["val"] = eval_split("VALIDATION", y_val, val_prob)
    if len(X_test):
        metrics["test"] = eval_split("TEST", y_test, test_prob)

    # Snimi model
    out_path = Path(args.out).resolve()
    joblib.dump(model, out_path)
    print(f"\n[train] saved model -> {out_path}")

    # Snimi meta 
    meta = {
        "trained_at": iso_z(datetime.now(timezone.utc)),
        "window_size": args.window,
        "feature_names": MODEL_FEATURE_NAMES,
        "label": "occupancy (0/1)",
        "model": "StandardScaler + LogisticRegression(class_weight=balanced)",
        "metrics": metrics,
        "data_file": str(data_path),
        "rows_raw": int(len(df)),
        "rows_features": int(len(df_feat)),
        "split_sizes": {"train": int(len(train_df)), "val": int(len(val_df)), "test": int(len(test_df))},
        "seed": args.seed,
    }
    meta_path = Path(args.meta).resolve()
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"[train] saved meta  -> {meta_path}")

    # Detaljniji report 
    if len(X_test):
        y_pred = (test_prob >= 0.5).astype(int)
        print("\n[train] classification_report (TEST):")
        print(classification_report(y_test, y_pred, digits=4, zero_division=0))

if __name__ == "__main__":
    main()