from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, TimeZone, UniversalText, id_key
from backend.plugin.production.enums import ProductionExecutionStatus


class WorkOrderMaterialAllocation(Base):
    """Immutable snapshot of an active BOM-to-operation material allocation."""

    __tablename__ = 'mes_work_order_material_allocation'
    __table_args__ = (
        sa.ForeignKeyConstraint(['work_order_id'], ['mes_work_order.id'], name='fk_wo_material_allocation_order'),
        sa.ForeignKeyConstraint(['requirement_id'], ['mes_work_order_material_requirement.id'], name='fk_wo_material_allocation_requirement'),
        sa.ForeignKeyConstraint(['work_order_operation_id'], ['mes_work_order_operation.id'], name='fk_wo_material_allocation_operation'),
        sa.UniqueConstraint('requirement_id', 'work_order_operation_id', 'deleted', name='uk_mes_wo_material_allocation'),
        {'comment': 'MES work-order material-to-operation allocation snapshots'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    work_order_id: Mapped[int] = mapped_column(sa.BigInteger)
    requirement_id: Mapped[int] = mapped_column(sa.BigInteger)
    work_order_operation_id: Mapped[int] = mapped_column(sa.BigInteger)
    planned_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))


class ProductionExecution(Base):
    """One operator execution session against a work-order operation snapshot."""

    __tablename__ = 'mes_production_execution'
    __table_args__ = (
        sa.ForeignKeyConstraint(['work_order_id'], ['mes_work_order.id'], name='fk_production_execution_order'),
        sa.ForeignKeyConstraint(['work_order_operation_id'], ['mes_work_order_operation.id'], name='fk_production_execution_operation'),
        sa.UniqueConstraint('execution_no', 'deleted', name='uk_mes_production_execution_no'),
        sa.Index('idx_mes_production_execution_order_status', 'work_order_id', 'status'),
        {'comment': 'MES work-order operation execution sessions'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    execution_no: Mapped[str] = mapped_column(sa.String(100))
    work_order_id: Mapped[int] = mapped_column(sa.BigInteger)
    work_order_operation_id: Mapped[int] = mapped_column(sa.BigInteger)
    started_at: Mapped[datetime] = mapped_column(TimeZone)
    status: Mapped[ProductionExecutionStatus] = mapped_column(
        sa.String(30),
        default=ProductionExecutionStatus.IN_PROGRESS,
        server_default=ProductionExecutionStatus.IN_PROGRESS.value,
    )
    good_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    scrap_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    completed_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    operator_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class MaterialConsumption(Base):
    """Actual material consumption captured during an operation execution."""

    __tablename__ = 'mes_material_consumption'
    __table_args__ = (
        sa.ForeignKeyConstraint(['execution_id'], ['mes_production_execution.id'], name='fk_material_consumption_execution'),
        sa.ForeignKeyConstraint(['requirement_id'], ['mes_work_order_material_requirement.id'], name='fk_material_consumption_requirement'),
        sa.ForeignKeyConstraint(['issue_line_id'], ['mes_material_issue_line.id'], name='fk_material_consumption_issue_line'),
        sa.ForeignKeyConstraint(['material_id'], ['mes_material.id'], name='fk_material_consumption_material'),
        sa.ForeignKeyConstraint(['lot_id'], ['mes_material_lot.id'], name='fk_material_consumption_lot'),
        sa.UniqueConstraint('consumption_no', 'deleted', name='uk_mes_material_consumption_no'),
        sa.Index('idx_mes_material_consumption_execution', 'execution_id'),
        sa.Index('idx_mes_material_consumption_requirement', 'requirement_id'),
        {'comment': 'MES actual material consumption records'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    consumption_no: Mapped[str] = mapped_column(sa.String(100))
    execution_id: Mapped[int] = mapped_column(sa.BigInteger)
    requirement_id: Mapped[int] = mapped_column(sa.BigInteger)
    material_id: Mapped[int] = mapped_column(sa.BigInteger)
    quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    consumed_at: Mapped[datetime] = mapped_column(TimeZone)
    issue_line_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    lot_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    operator_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)
