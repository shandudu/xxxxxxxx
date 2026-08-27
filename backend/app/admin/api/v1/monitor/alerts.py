from typing import Annotated

from fastapi import APIRouter, Query

from backend.app.admin.schema.monitor_alert import AlertInboxSummary
from backend.app.admin.service.alert_service import alert_service
from backend.common.response.response_schema import ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db import CurrentSession

router = APIRouter()


@router.get('', summary='获取统一预警中心', dependencies=[DependsJwtAuth])
async def get_alert_inbox(
    db: CurrentSession,
    source: Annotated[str | None, Query(description='告警来源')] = None,
    status: Annotated[str | None, Query(description='统一状态')] = None,
    limit: Annotated[int, Query(ge=1, le=500, description='最多返回条数')] = 100,
) -> ResponseSchemaModel[AlertInboxSummary]:
    data = await alert_service.inbox(db, source=source, status=status, limit=limit)
    return response_base.success(data=data)
