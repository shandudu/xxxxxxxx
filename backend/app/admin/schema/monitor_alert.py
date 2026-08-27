from datetime import datetime
from typing import Any

from pydantic import Field

from backend.common.schema import SchemaBase


class AlertInboxItem(SchemaBase):
    """统一预警中心的一条可定位业务告警。"""

    source: str = Field(description='告警来源：QUALITY/ANDON/INVENTORY/SALES/PURCHASING')
    alert_type: str = Field(description='告警类型')
    alert_id: int = Field(description='来源业务记录 ID')
    code: str = Field(description='业务单号或告警编号')
    title: str = Field(description='告警标题')
    severity: str = Field(description='严重级别')
    status: str = Field(description='统一状态')
    due_at: datetime | None = Field(default=None, description='处理截止时间')
    owner_id: int | None = Field(default=None, description='责任人 ID')
    action_path: str = Field(description='前端处理入口')
    details: dict[str, Any] = Field(default_factory=dict, description='来源域明细')


class AlertInboxSummary(SchemaBase):
    """统一预警中心汇总。"""

    total: int = Field(description='告警总数')
    open_count: int = Field(description='未关闭告警数')
    overdue_count: int = Field(description='逾期告警数')
    by_source: dict[str, int] = Field(description='按来源统计')
    items: list[AlertInboxItem] = Field(description='告警明细')
