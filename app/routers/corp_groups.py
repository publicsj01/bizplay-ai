# 법인 그룹 라우터 — Spring AI CorpGroupController.java 1:1 대응
# POST   /api/v1/corp-groups
# GET    /api/v1/corp-groups
# GET    /api/v1/corp-groups/{id}
# PUT    /api/v1/corp-groups/{id}
# DELETE /api/v1/corp-groups/{id}

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.schemas import ApiResponse, CorpGroupCreateRequest, CorpGroupUpdateRequest
from app.services.corp import (
    create_corp_group,
    delete_corp_group,
    get_corp_group,
    list_corp_groups,
    update_corp_group,
)

router = APIRouter(prefix="/api/v1/corp-groups", tags=["corp-groups"])


@router.get("", response_model=ApiResponse)
async def list_groups(db: AsyncSession = Depends(get_db)) -> ApiResponse:
    data = await list_corp_groups(db)
    return ApiResponse(success=True, data=[d.model_dump() for d in data])


@router.get("/{group_id}", response_model=ApiResponse)
async def get_group(group_id: int, db: AsyncSession = Depends(get_db)) -> ApiResponse:
    data = await get_corp_group(db, group_id)
    return ApiResponse(success=True, data=data.model_dump())


@router.post("", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    req: CorpGroupCreateRequest, db: AsyncSession = Depends(get_db)
) -> ApiResponse:
    data = await create_corp_group(db, req)
    return ApiResponse(success=True, data=data.model_dump())


@router.put("/{group_id}", response_model=ApiResponse)
async def update_group(
    group_id: int, req: CorpGroupUpdateRequest, db: AsyncSession = Depends(get_db)
) -> ApiResponse:
    data = await update_corp_group(db, group_id, req)
    return ApiResponse(success=True, data=data.model_dump())


@router.delete("/{group_id}", response_model=ApiResponse)
async def delete_group(group_id: int, db: AsyncSession = Depends(get_db)) -> ApiResponse:
    await delete_corp_group(db, group_id)
    return ApiResponse(success=True, message="Corp group deleted")
