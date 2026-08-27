from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, TimeZone, UniversalText, id_key
from backend.plugin.demo.enums import DemoRunStatus


class ManufacturingDemoRun(Base):
    """Audit record for one logical run of the fixed happy-path scenario."""

    __tablename__ = 'mes_demo_run'
    __table_args__ = (
        sa.UniqueConstraint('scenario_code', 'deleted', name='uk_mes_demo_run_scenario_deleted'),
        sa.Index('idx_mes_demo_run_status', 'status'),
        {'comment': 'MES repeatable manufacturing demo runs'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    run_no: Mapped[str] = mapped_column(sa.String(100))
    scenario_code: Mapped[str] = mapped_column(sa.String(80))
    started_at: Mapped[datetime] = mapped_column(TimeZone)
    status: Mapped[DemoRunStatus] = mapped_column(sa.String(20), default=DemoRunStatus.RUNNING)
    completed_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    failed_step: Mapped[str | None] = mapped_column(sa.String(80), default=None)
    error_message: Mapped[str | None] = mapped_column(UniversalText, default=None)
    created_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)
    updated_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)
