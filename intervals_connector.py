"""intervals_connector.py — Conector con intervals.icu.
Auth HTTP Basic: usuario "API_KEY", password = tu API key.
"""
from __future__ import annotations
from datetime import date, datetime, timedelta
from training_engine import Activity

try:
    import requests
except ImportError:
    requests = None

BASE_URL = "https://intervals.icu/api/v1"
RIDE_TYPES = {"Ride", "VirtualRide", "GravelRide", "MountainBikeRide", "EBikeRide"}


def _to_date(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def parse_activity(raw):
    if raw.get("type") and raw["type"] not in RIDE_TYPES:
        return None
    day = _to_date(raw.get("start_date_local") or raw.get("start_date"))
    if day is None:
        return None
    tss = raw.get("icu_training_load")
    if tss is None:
        tss = raw.get("training_load") or 0
    return Activity(
        day=day,
        tss=round(float(tss or 0), 1),
        np_watts=raw.get("icu_weighted_avg_watts") or raw.get("normalized_watts"),
        ftp_at_time=raw.get("icu_ftp"),
        duration_s=raw.get("moving_time") or raw.get("elapsed_time"),
        best_5min_w=(raw.get("icu_pm_p300") or raw.get("p300")),
        elev_gain_m=raw.get("total_elevation_gain") or raw.get("icu_elevation_gain"),
        name=raw.get("name"),
    )


class IntervalsClient:
    def __init__(self, athlete_id, api_key):
        if requests is None:
            raise RuntimeError("Instala 'requests'")
        self.athlete_id = athlete_id
        self.session = requests.Session()
        self.session.auth = ("API_KEY", api_key)

    def get_activities(self, oldest, newest):
        url = f"{BASE_URL}/athlete/{self.athlete_id}/activities"
        r = self.session.get(url, params={"oldest": oldest, "newest": newest}, timeout=30)
        r.raise_for_status()
        out = []
        for raw in r.json():
            act = parse_activity(raw)
            if act:
                out.append(act)
        return sorted(out, key=lambda a: a.day)

    def get_athlete_ftp(self):
        url = f"{BASE_URL}/athlete/{self.athlete_id}"
        r = self.session.get(url, timeout=30)
        r.raise_for_status()
        data = r.json()
        if data.get("icu_ftp"):
            return data["icu_ftp"]
        for s in data.get("sportSettings", []) or []:
            if s.get("ftp"):
                return s["ftp"]
        return None

    def push_planned_workout(self, day, name, description, sport="Ride"):
        """Crea el entreno planeado en el calendario de intervals.icu.
        Con 'Cargar entrenamientos planificados' activo, sincroniza a Garmin."""
        payload = {
            "category": "WORKOUT",
            "start_date_local": f"{day}T00:00:00",
            "type": sport,
            "name": name,
            "description": description,
        }
        url = f"{BASE_URL}/athlete/{self.athlete_id}/events"
        r = self.session.post(url, json=payload, timeout=30)
        r.raise_for_status()
        return r.json()
