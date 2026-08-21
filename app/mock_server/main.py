import random
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException

app = FastAPI(title="Mock Third-Party APIs")

FAILING: set[str] = set()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _guard(source: str) -> None:
    if source in FAILING:
        raise HTTPException(status_code=503, detail=f"{source} is down (simulated)")


@app.get("/iot")
def iot() -> list[dict]:
    _guard("iot")
    return [
        {
            "device_id": random.choice(["solar-1", "battery-2", "wind-3", "grid-4"]),
            "timestamp": _now(),
            "power_kw": round(random.uniform(-10, 50), 3),
            "voltage_v": round(random.uniform(220, 240), 2),
        }
    ]


@app.get("/weather")
def weather() -> list[dict]:
    _guard("weather")
    return [
        {
            "timestamp": _now(),
            "location": random.choice(["berlin", "amsterdam", "lisbon"]),
            "temperature_c": round(random.uniform(-5, 40), 2),
            "wind_speed_ms": round(random.uniform(0, 30), 2),
            "solar_irradiance_wm2": round(random.uniform(0, 1000), 2),
        }
    ]


@app.get("/market")
def market() -> list[dict]:
    _guard("market")
    return [
        {
            "timestamp": _now(),
            "region": random.choice(["de", "nl", "pt"]),
            "price_per_kwh": round(random.uniform(0.05, 0.60), 4),
            "currency": "EUR",
        }
    ]


@app.post("/_control/{source}/fail")
def fail(source: str) -> dict[str, str]:
    FAILING.add(source)
    return {"source": source, "status": "failing"}


@app.post("/_control/{source}/recover")
def recover(source: str) -> dict[str, str]:
    FAILING.discard(source)
    return {"source": source, "status": "recovered"}
