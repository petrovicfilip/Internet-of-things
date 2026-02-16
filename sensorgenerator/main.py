import os
import csv
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import httpx
from dateutil import parser as dtparser
from dateutil import tz



def env(name: str, default: str) -> str:
    v = os.getenv(name)
    return v if v is not None and v != "" else default


@dataclass
class Config:
    gateway_url: str
    data_file: str
    mode: str               # fixed | replay
    interval_ms: int        # used in fixed
    speed: float            # used in replay (npr 60 => 60x brže)
    limit: int              # 0 = bez limita
    loop: bool              # ponavljaj fajl
    timeout_s: float


def sniff_delimiter(path: str) -> str:
    with open(path, "r", newline="", encoding="utf-8") as f:
        sample = f.read(4096)
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=[",", ";", "\t"])
        return dialect.delimiter
    except Exception:
        return ","


def pick(d: Dict[str, str], *keys: str) -> Optional[str]:
    for k in keys:
        if k in d and d[k] is not None and str(d[k]).strip() != "":
            return d[k]
    return None


def parse_ts(row: Dict[str, str]) -> str:
    # pokušaj tipične kolone
    raw = pick(row, "ts", "timestamp", "time", "date", "Date", "datetime", "DateTime")
    if not raw:
        raise ValueError("Nema timestamp kolone (ts/timestamp/date/...)")

    dt = dtparser.parse(raw)
    # ako nema timezone, tretiraj kao UTC (dataset često nema tz)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz.UTC)
    return dt.astimezone(tz.UTC).isoformat().replace("+00:00", "Z")


def parse_float(row: Dict[str, str], *keys: str, default: float = 0.0) -> float:
    v = pick(row, *keys)
    if v is None:
        return default
    try:
        return float(v)
    except Exception:
        return default


def parse_bool(row: Dict[str, str], *keys: str, default: bool = False) -> bool:
    v = pick(row, *keys)
    if v is None:
        return default
    s = str(v).strip().lower()
    if s in ("1", "true", "yes", "y", "t"):
        return True
    if s in ("0", "false", "no", "n", "f"):
        return False
    return default


def map_row_to_payload(row: Dict[str, str], source_id: int) -> Dict:
    # Mapiranje kolona iz occupancy dataset-a:
    # Temperature, Humidity, Light, CO2, HumidityRatio, Occupancy, date
    ts = parse_ts(row)

    payload = {
        "source_id": source_id,
        "ts": ts,
        "temperature_c": parse_float(row, "temperature_c", "Temperature", "temperature", "temp", "Temp"),
        "humidity_percent": parse_float(row, "humidity_percent", "Humidity", "humidity"),
        "light_lux": parse_float(row, "light_lux", "Light", "light"),
        "co2_ppm": parse_float(row, "co2_ppm", "CO2", "co2"),
        "humidity_ratio": parse_float(row, "humidity_ratio", "HumidityRatio", "humidityratio", "hum_ratio"),
        "occupancy": parse_bool(row, "occupancy", "Occupancy", default=False),
    }
    return payload


def send_with_retry(client: httpx.Client, url: str, json: Dict, max_tries: int = 5) -> Tuple[bool, Optional[str]]:
    delay = 0.5
    for attempt in range(1, max_tries + 1):
        try:
            r = client.post(url, json=json)
            if 200 <= r.status_code < 300:
                # očekujemo {"reading": {...}}
                rid = None
                try:
                    rid = r.json().get("reading", {}).get("id")
                except Exception:
                    rid = None
                return True, rid
            # 4xx: loš payload (nema smisla retry mnogo)
            if 400 <= r.status_code < 500:
                return False, f"{r.status_code} {r.text}"
        except Exception as e:
            last_err = str(e)

        time.sleep(delay)
        delay = min(delay * 2, 5.0)

    return False, locals().get("last_err", "unknown error")


def main():
    cfg = Config(
        gateway_url=env("GATEWAY_URL", "http://localhost:3000/api/v1/readings"),
        data_file=env("DATA_FILE", "./data/processed/occupancy_readings.csv"),
        mode=env("MODE", "fixed").lower(),          # fixed | replay
        interval_ms=int(env("INTERVAL_MS", "200")), # fixed mode: 200ms
        speed=float(env("SPEED", "60")),            # replay mode: 60x brže
        limit=int(env("LIMIT", "5000")),               # 0 = bez limita
        loop=env("LOOP", "false").lower() in ("1", "true", "yes", "y"),
        timeout_s=float(env("TIMEOUT_S", "10")),
    )

    print(f"[sensorgenerator] url={cfg.gateway_url} file={cfg.data_file} mode={cfg.mode} interval_ms={cfg.interval_ms} speed={cfg.speed} limit={cfg.limit} loop={cfg.loop}")

    if not os.path.exists(cfg.data_file):
        raise FileNotFoundError(f"DATA_FILE ne postoji: {cfg.data_file}")

    delim = sniff_delimiter(cfg.data_file)
    print(f"[sensorgenerator] file={cfg.data_file} delim='{delim}' mode={cfg.mode}")

    with httpx.Client(timeout=cfg.timeout_s) as client:
        total_sent = 0
        file_round = 0

        while True:
            file_round += 1
            prev_ts_epoch: Optional[float] = None

            with open(cfg.data_file, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter=delim)

                for idx, row in enumerate(reader, start=1):
                    # limit
                    if cfg.limit > 0 and total_sent >= cfg.limit:
                        print(f"[sensorgenerator] LIMIT reached: {cfg.limit}")
                        return

                    payload = map_row_to_payload(row, source_id=idx + (file_round - 1) * 1_000_000)

                    # pacing
                    if cfg.mode == "replay":
                        # sleep based on delta(ts)/speed
                        try:
                            ts_iso = payload["ts"]
                            dt = dtparser.parse(ts_iso)
                            cur_epoch = dt.timestamp()
                            if prev_ts_epoch is not None:
                                delta = max(0.0, cur_epoch - prev_ts_epoch)
                                sleep_s = delta / max(cfg.speed, 0.0001)
                                if sleep_s > 0:
                                    time.sleep(min(sleep_s, 2.0))  # safety cap
                            prev_ts_epoch = cur_epoch
                        except Exception:
                            # fallback fixed small sleep
                            time.sleep(cfg.interval_ms / 1000.0)
                    else:
                        time.sleep(cfg.interval_ms / 1000.0)

                    ok, info = send_with_retry(client, cfg.gateway_url, payload)
                    total_sent += 1

                    if ok:
                        print(f"[sent #{total_sent}] id={info} ts={payload['ts']}")
                    else:
                        print(f"[fail #{total_sent}] {info}")

            if not cfg.loop:
                break

        print(f"[sensorgenerator] done. total_sent={total_sent}")


if __name__ == "__main__":
    main()