# 법인(Corporation) + 법인그룹(CorpGroup) CRUD 서비스
# Spring AI: CorpService.java + CorpGroupService.java 1:1 대응

from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import CorpGroup, Corporation
from app.models.schemas import (
    CorpCreateRequest,
    CorpGroupCreateRequest,
    CorpGroupResponse,
    CorpGroupUpdateRequest,
    CorpResponse,
    CorpUpdateRequest,
)


# ── CorpGroup ──────────────────────────────────────────────────────────────────

async def list_corp_groups(db: AsyncSession) -> List[CorpGroupResponse]:
    result = await db.execute(
        select(CorpGroup).order_by(CorpGroup.corp_group_cd.asc())
    )
    return [CorpGroupResponse.model_validate(g) for g in result.scalars().all()]


async def get_corp_group(db: AsyncSession, group_id: int) -> CorpGroupResponse:
    g = await db.get(CorpGroup, group_id)
    if not g:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Corp group not found: id={group_id}")
    return CorpGroupResponse.model_validate(g)


async def create_corp_group(db: AsyncSession, req: CorpGroupCreateRequest) -> CorpGroupResponse:
    exists = await db.scalar(
        select(func.count()).where(CorpGroup.corp_group_cd == req.corp_group_cd)
    )
    if exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Corp group already exists: corp_group_cd={req.corp_group_cd}",
        )
    g = CorpGroup(corp_group_cd=req.corp_group_cd)
    db.add(g)
    await db.flush()
    return CorpGroupResponse.model_validate(g)


async def update_corp_group(
    db: AsyncSession, group_id: int, req: CorpGroupUpdateRequest
) -> CorpGroupResponse:
    g = await db.get(CorpGroup, group_id)
    if not g:
        raise HTTPException(status_code=404, detail=f"Corp group not found: id={group_id}")

    if req.corp_group_cd and req.corp_group_cd != g.corp_group_cd:
        exists = await db.scalar(
            select(func.count()).where(CorpGroup.corp_group_cd == req.corp_group_cd)
        )
        if exists:
            raise HTTPException(
                status_code=409,
                detail=f"Corp group already exists: corp_group_cd={req.corp_group_cd}",
            )
        g.corp_group_cd = req.corp_group_cd

    await db.flush()
    return CorpGroupResponse.model_validate(g)


async def delete_corp_group(db: AsyncSession, group_id: int) -> None:
    """
    그룹에 소속된 법인이 있으면 삭제 거부.
    Spring AI: CorpGroupService.delete() 명시적 사전 체크 대응
    (DB CASCADE가 있어도 서비스 레이어에서 차단)
    """
    g = await db.get(CorpGroup, group_id)
    if not g:
        raise HTTPException(status_code=404, detail=f"Corp group not found: id={group_id}")

    corp_count = await db.scalar(
        select(func.count()).where(Corporation.corp_group_id == group_id)
    )
    if corp_count:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete corp_group: {corp_count} corp(s) still reference it. Move or delete those corps first.",
        )
    await db.delete(g)


# ── Corporation ────────────────────────────────────────────────────────────────

async def list_corps(
    db: AsyncSession, corp_group_id: Optional[int] = None
) -> List[CorpResponse]:
    """
    전체 목록 또는 corp_group_id 필터 목록 반환.
    Spring AI: CorpService.list(corpGroupId) 대응
    """
    stmt = select(Corporation)
    if corp_group_id is not None:
        stmt = stmt.where(Corporation.corp_group_id == corp_group_id)
    stmt = stmt.order_by(Corporation.corp_no.asc())
    result = await db.execute(stmt)
    return [CorpResponse.model_validate(c) for c in result.scalars().all()]


async def get_corp(db: AsyncSession, corp_no: str) -> CorpResponse:
    result = await db.execute(select(Corporation).where(Corporation.corp_no == corp_no))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail=f"Corporation not found: corp_no={corp_no}")
    return CorpResponse.model_validate(c)


async def create_corp(db: AsyncSession, req: CorpCreateRequest) -> CorpResponse:
    exists = await db.scalar(
        select(func.count()).where(Corporation.corp_no == req.corp_no)
    )
    if exists:
        raise HTTPException(
            status_code=409,
            detail=f"Corporation already exists: corp_no={req.corp_no}",
        )
    group = await db.get(CorpGroup, req.corp_group_id)
    if not group:
        raise HTTPException(
            status_code=404,
            detail=f"Corp group not found: id={req.corp_group_id}",
        )
    c = Corporation(
        corp_no=req.corp_no,
        corp_group_id=req.corp_group_id,
        corp_name=req.corp_name,
    )
    db.add(c)
    await db.flush()
    return CorpResponse.model_validate(c)


async def update_corp(
    db: AsyncSession, corp_no: str, req: CorpUpdateRequest
) -> CorpResponse:
    """
    corp_no는 경로 식별자로 변경 불가.
    Spring AI: CorpService.update() PATCH 시맨틱 대응
    """
    result = await db.execute(select(Corporation).where(Corporation.corp_no == corp_no))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail=f"Corporation not found: corp_no={corp_no}")

    if req.corp_group_id is not None:
        group = await db.get(CorpGroup, req.corp_group_id)
        if not group:
            raise HTTPException(status_code=404, detail=f"Corp group not found: id={req.corp_group_id}")
        c.corp_group_id = req.corp_group_id

    if req.corp_name is not None:
        c.corp_name = req.corp_name

    await db.flush()
    return CorpResponse.model_validate(c)


async def delete_corp(db: AsyncSession, corp_no: str) -> None:
    """
    법인 삭제. Bot.corp_no는 soft ref이므로 Bot에 영향 없음.
    Spring AI: CorpService.delete() 대응
    """
    result = await db.execute(select(Corporation).where(Corporation.corp_no == corp_no))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail=f"Corporation not found: corp_no={corp_no}")
    await db.delete(c)
