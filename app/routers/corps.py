# 법인 라우터 — Spring AI CorpController.java 1:1 대응
# POST   /api/v1/corps
# GET    /api/v1/corps          (optional ?corp_group_id=N)
# GET    /api/v1/corps/{corpNo}
# PUT    /api/v1/corps/{corpNo}
# DELETE /api/v1/corps/{corpNo}

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.schemas import ApiResponse, CorpCreateRequest, CorpUpdateRequest
from app.services.corp import (
    create_corp,
    delete_corp,
    get_corp,
    list_corps,
    update_corp,
)

router = APIRouter(prefix="/api/v1/corps", tags=["corps"])


@router.get("", response_model=ApiResponse)
async def list_corporations(
    corp_group_id: Optional[int] = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """
    전체 법인 목록 반환. corp_group_id 쿼리 파라미터로 필터 가능.
    Spring AI: CorpController.list(?corpGroupId=N) 대응
    알 수 없는 corp_no → 빈 리스트 반환 (404 아님, soft ref 설계)
    """
    data = await list_corps(db, corp_group_id)
    return ApiResponse(success=True, data=[d.model_dump() for d in data])


@router.get("/{corp_no}", response_model=ApiResponse)
async def get_corporation(corp_no: str, db: AsyncSession = Depends(get_db)) -> ApiResponse:
    data = await get_corp(db, corp_no)
    return ApiResponse(success=True, data=data.model_dump())


@router.post("", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def create_corporation(
    req: CorpCreateRequest, db: AsyncSession = Depends(get_db)
) -> ApiResponse:
    data = await create_corp(db, req)
    return ApiResponse(success=True, data=data.model_dump())


@router.put("/{corp_no}", response_model=ApiResponse)
async def update_corporation(
    corp_no: str, req: CorpUpdateRequest, db: AsyncSession = Depends(get_db)
) -> ApiResponse:
    """
    corp_no는 경로 식별자로 변경 불가 (PATCH 시맨틱).
    Spring AI: CorpController.update() 대응
    """
    data = await update_corp(db, corp_no, req)
    return ApiResponse(success=True, data=data.model_dump())


@router.delete("/{corp_no}", response_model=ApiResponse)
async def delete_corporation(corp_no: str, db: AsyncSession = Depends(get_db)) -> ApiResponse:
    """
    법인 삭제. Bot.corp_no는 soft ref이므로 Bot에는 영향 없음.
    Spring AI: CorpController.delete() 대응
    """
    await delete_corp(db, corp_no)
    return ApiResponse(success=True, message="Corporation deleted")
