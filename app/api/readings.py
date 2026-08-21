from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import DB_SOURCE_MODELS
from app.schemas import API_SOURCE_SCHEMAS

router = APIRouter(tags=["readings"])


@router.get("/readings/{source}")
async def readings(
    source: str,
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    '''
    Returns the last limit readings for a given source.
    '''
    model_cls = DB_SOURCE_MODELS.get(source) # get() returns None if no key found
    if model_cls is None:
        raise HTTPException(status_code=404, detail=f"Unknown source: {source!r}")
    schema_cls = API_SOURCE_SCHEMAS[source]

    result = await session.execute(
        select(model_cls).order_by(model_cls.id.desc()).limit(limit)
    )
    rows = result.scalars().all()
    return [schema_cls.model_validate(row).model_dump() for row in rows]
