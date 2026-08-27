from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, UniversalText, id_key
from backend.plugin.routing.enums import WorkCenterStatus, WorkCenterType


class WorkCenter(Base):
    """MES logical capacity unit; it is not an equipment instance."""

    __tablename__ = 'mes_work_center'
    __table_args__ = (
        sa.UniqueConstraint('work_center_code', 'deleted', name='uk_mes_work_center_code_deleted'),
        sa.Index('idx_mes_work_center_status', 'status'),
        sa.Index('idx_mes_work_center_type', 'work_center_type'),
        sa.Index('idx_mes_work_center_factory', 'factory_code'),
        {'comment': 'MES logical manufacturing work centers'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    work_center_code: Mapped[str] = mapped_column(sa.String(80), comment='工作中心编码')
    work_center_name: Mapped[str] = mapped_column(sa.String(150), comment='工作中心名称')
    work_center_type: Mapped[WorkCenterType] = mapped_column(sa.String(30), default=WorkCenterType.OTHER)
    factory_code: Mapped[str | None] = mapped_column(sa.String(50), default=None)
    workshop_code: Mapped[str | None] = mapped_column(sa.String(50), default=None)
    location_description: Mapped[str | None] = mapped_column(sa.String(200), default=None)
    status: Mapped[WorkCenterStatus] = mapped_column(
        sa.String(20), default=WorkCenterStatus.ACTIVE, server_default=WorkCenterStatus.ACTIVE.value
    )
    production_enabled: Mapped[bool] = mapped_column(default=True, server_default=sa.true())
    scheduling_enabled: Mapped[bool] = mapped_column(default=True, server_default=sa.true())
    capacity_value: Mapped[Decimal | None] = mapped_column(sa.Numeric(18, 6), default=None)
    capacity_unit: Mapped[str | None] = mapped_column(sa.String(30), default=None)
    parallel_capacity: Mapped[int] = mapped_column(sa.Integer, default=1, server_default='1')
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)
    sort_no: Mapped[int] = mapped_column(sa.Integer, default=0, server_default='0')
    created_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)
    updated_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)
