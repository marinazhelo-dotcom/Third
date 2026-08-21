from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.telemetry.app.db import get_session
from services.telemetry.app.models import Reading

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/devices")
async def devices(session: AsyncSession = Depends(get_session)) -> list[str]:
    result = await session.execute(select(Reading.device_id).distinct())
    return sorted(row[0] for row in result.all())


@router.get("/devices/{device_id}/latest")
async def latest(device_id: str, request: Request) -> dict:
    reading = await request.app.state.cache.get_latest(device_id)
    if reading is None:
        raise HTTPException(status_code=404, detail=f"No reading for device {device_id!r}")
    return reading


@router.get("/devices/{device_id}/readings")
async def readings(
    device_id: str,
    limit: int = Query(default=50, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    result = await session.execute(
        select(Reading)
        .where(Reading.device_id == device_id)
        .order_by(Reading.timestamp.desc())
        .limit(limit)
    )
    rows = result.scalars().all()
    return [
        {
            "timestamp": row.timestamp,
            "power_kw": row.power_kw,
            "voltage_v": row.voltage_v,
        }
        for row in rows
    ]


@router.get("/devices/{device_id}/stats")
async def stats(
    device_id: str,
    window_seconds: int = Query(default=3600, ge=1),
    session: AsyncSession = Depends(get_session),
) -> dict:
    since = datetime.now(timezone.utc) - timedelta(seconds=window_seconds)
    result = await session.execute(
        select(
            func.count().label("count"),
            func.avg(Reading.power_kw).label("avg_power_kw"),
            func.min(Reading.power_kw).label("min_power_kw"),
            func.max(Reading.power_kw).label("max_power_kw"),
            func.avg(Reading.voltage_v).label("avg_voltage_v"),
        ).where(Reading.device_id == device_id, Reading.timestamp >= since)
    )
    row = result.one()
    if row.count == 0:
        raise HTTPException(
            status_code=404,
            detail=f"No readings for device {device_id!r} in the last {window_seconds}s",
        )
    return {
        "device_id": device_id,
        "window_seconds": window_seconds,
        "count": row.count,
        "avg_power_kw": round(row.avg_power_kw, 4),
        "min_power_kw": round(row.min_power_kw, 4),
        "max_power_kw": round(row.max_power_kw, 4),
        "avg_voltage_v": round(row.avg_voltage_v, 2),
    }
