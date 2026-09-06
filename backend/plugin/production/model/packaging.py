from datetime import date, datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, TimeZone, UniversalText, id_key
from backend.plugin.production.packaging_enums import (
    HandlingUnitStatus,
    HandlingUnitType,
    PackagingInspectionResult,
    PackagingScanType,
    PackagingSpecStatus,
    PackagingTaskStatus,
    WeightCheckResult,
)


class PackagingSpecification(Base):
    """Versioned finished-goods packaging rule."""

    __tablename__ = 'mes_packaging_specification'
    __table_args__ = (
        sa.ForeignKeyConstraint(['material_id'], ['mes_material.id'], name='fk_packaging_spec_material'),
        sa.UniqueConstraint('spec_code', 'version', 'deleted', name='uk_packaging_spec_code_version'),
        sa.Index('idx_packaging_spec_material_status', 'material_id', 'status'),
        {'comment': 'Finished-goods packaging specifications'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    spec_code: Mapped[str] = mapped_column(sa.String(80))
    spec_name: Mapped[str] = mapped_column(sa.String(150))
    material_id: Mapped[int] = mapped_column(sa.BigInteger)
    units_per_carton: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    version: Mapped[str] = mapped_column(sa.String(30), default='V1', server_default='V1')
    cartons_per_pallet: Mapped[int | None] = mapped_column(default=None)
    allow_mixed_lot: Mapped[bool] = mapped_column(default=False, server_default=sa.false())
    allow_partial_carton: Mapped[bool] = mapped_column(default=False, server_default=sa.false())
    require_quality_release: Mapped[bool] = mapped_column(default=True, server_default=sa.true())
    require_weight_check: Mapped[bool] = mapped_column(default=False, server_default=sa.false())
    target_gross_weight: Mapped[Decimal | None] = mapped_column(sa.Numeric(18, 6), default=None)
    weight_tolerance: Mapped[Decimal | None] = mapped_column(sa.Numeric(18, 6), default=None)
    label_template_code: Mapped[str | None] = mapped_column(sa.String(80), default=None)
    effective_from: Mapped[date | None] = mapped_column(default=None)
    effective_to: Mapped[date | None] = mapped_column(default=None)
    status: Mapped[PackagingSpecStatus] = mapped_column(
        sa.String(20), default=PackagingSpecStatus.ACTIVE, server_default=PackagingSpecStatus.ACTIVE.value
    )
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class PackagingTask(Base):
    """Packaging task sourced from one posted production report."""

    __tablename__ = 'mes_packaging_task'
    __table_args__ = (
        sa.ForeignKeyConstraint(['production_report_id'], ['mes_production_report.id'], name='fk_packaging_task_report'),
        sa.ForeignKeyConstraint(['work_order_id'], ['mes_work_order.id'], name='fk_packaging_task_order'),
        sa.ForeignKeyConstraint(['material_id'], ['mes_material.id'], name='fk_packaging_task_material'),
        sa.ForeignKeyConstraint(['lot_id'], ['mes_material_lot.id'], name='fk_packaging_task_lot'),
        sa.ForeignKeyConstraint(['specification_id'], ['mes_packaging_specification.id'], name='fk_packaging_task_spec'),
        sa.ForeignKeyConstraint(['stock_transaction_id'], ['mes_stock_transaction.id'], name='fk_packaging_task_stock_tx'),
        sa.UniqueConstraint('task_no', 'deleted', name='uk_packaging_task_no_deleted'),
        sa.UniqueConstraint('idempotency_key', 'deleted', name='uk_packaging_task_idempotency'),
        sa.Index('idx_packaging_task_report', 'production_report_id'),
        sa.Index('idx_packaging_task_status', 'status'),
        {'comment': 'Finished-goods packaging tasks'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    task_no: Mapped[str] = mapped_column(sa.String(100))
    production_report_id: Mapped[int] = mapped_column(sa.BigInteger)
    work_order_id: Mapped[int] = mapped_column(sa.BigInteger)
    material_id: Mapped[int] = mapped_column(sa.BigInteger)
    specification_id: Mapped[int] = mapped_column(sa.BigInteger)
    planned_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    lot_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    stock_transaction_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    idempotency_key: Mapped[str | None] = mapped_column(sa.String(180), default=None)
    packed_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    status: Mapped[PackagingTaskStatus] = mapped_column(
        sa.String(30), default=PackagingTaskStatus.DRAFT, server_default=PackagingTaskStatus.DRAFT.value
    )
    started_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    packed_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    released_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class PackagingHandlingUnit(Base):
    """Scannable inner pack, carton or pallet."""

    __tablename__ = 'mes_packaging_handling_unit'
    __table_args__ = (
        sa.ForeignKeyConstraint(['task_id'], ['mes_packaging_task.id'], name='fk_packaging_hu_task'),
        sa.ForeignKeyConstraint(['parent_hu_id'], ['mes_packaging_handling_unit.id'], name='fk_packaging_hu_parent'),
        sa.UniqueConstraint('hu_code', 'deleted', name='uk_packaging_hu_code_deleted'),
        sa.Index('idx_packaging_hu_task_status', 'task_id', 'status'),
        {'comment': 'Packaging handling units (HU)'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    hu_code: Mapped[str] = mapped_column(sa.String(120))
    task_id: Mapped[int] = mapped_column(sa.BigInteger)
    hu_type: Mapped[HandlingUnitType] = mapped_column(sa.String(20))
    capacity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    parent_hu_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6), default=Decimal('0'), server_default='0')
    tare_weight: Mapped[Decimal | None] = mapped_column(sa.Numeric(18, 6), default=None)
    gross_weight: Mapped[Decimal | None] = mapped_column(sa.Numeric(18, 6), default=None)
    net_weight: Mapped[Decimal | None] = mapped_column(sa.Numeric(18, 6), default=None)
    weight_result: Mapped[WeightCheckResult | None] = mapped_column(sa.String(20), default=None)
    status: Mapped[HandlingUnitStatus] = mapped_column(
        sa.String(30), default=HandlingUnitStatus.OPEN, server_default=HandlingUnitStatus.OPEN.value
    )
    sealed_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    released_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    stored_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    version: Mapped[int] = mapped_column(default=1, server_default='1')
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class PackagingHandlingUnitContent(Base):
    """Immutable scan line linking a HU to a lot or serial."""

    __tablename__ = 'mes_packaging_hu_content'
    __table_args__ = (
        sa.ForeignKeyConstraint(['hu_id'], ['mes_packaging_handling_unit.id'], name='fk_packaging_content_hu'),
        sa.ForeignKeyConstraint(['material_id'], ['mes_material.id'], name='fk_packaging_content_material'),
        sa.ForeignKeyConstraint(['lot_id'], ['mes_material_lot.id'], name='fk_packaging_content_lot'),
        sa.ForeignKeyConstraint(['serial_id'], ['mes_material_serial.id'], name='fk_packaging_content_serial'),
        sa.ForeignKeyConstraint(['production_report_id'], ['mes_production_report.id'], name='fk_packaging_content_report'),
        sa.UniqueConstraint('scan_key', 'deleted', name='uk_packaging_content_scan_key'),
        sa.Index('idx_packaging_content_hu', 'hu_id'),
        sa.Index('idx_packaging_content_serial', 'serial_id'),
        {'comment': 'Lot and serial contents scanned into packaging HUs'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    hu_id: Mapped[int] = mapped_column(sa.BigInteger)
    material_id: Mapped[int] = mapped_column(sa.BigInteger)
    production_report_id: Mapped[int] = mapped_column(sa.BigInteger)
    scan_type: Mapped[PackagingScanType] = mapped_column(sa.String(20))
    scanned_code: Mapped[str] = mapped_column(sa.String(120))
    quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    scan_key: Mapped[str] = mapped_column(sa.String(180))
    lot_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    serial_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    scanned_by: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)


class PackagingWeightRecord(Base):
    """Auditable weighing record for a handling unit."""

    __tablename__ = 'mes_packaging_weight_record'
    __table_args__ = (
        sa.ForeignKeyConstraint(['hu_id'], ['mes_packaging_handling_unit.id'], name='fk_packaging_weight_hu'),
        sa.UniqueConstraint('idempotency_key', 'deleted', name='uk_packaging_weight_idempotency'),
        {'comment': 'Packaging weight checks'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    hu_id: Mapped[int] = mapped_column(sa.BigInteger)
    gross_weight: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    tare_weight: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    net_weight: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    result: Mapped[WeightCheckResult] = mapped_column(sa.String(20))
    idempotency_key: Mapped[str] = mapped_column(sa.String(180))
    measured_by: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class PackagingInspection(Base):
    """Packaging appearance, quantity and label release decision."""

    __tablename__ = 'mes_packaging_inspection'
    __table_args__ = (
        sa.ForeignKeyConstraint(['hu_id'], ['mes_packaging_handling_unit.id'], name='fk_packaging_inspection_hu'),
        sa.UniqueConstraint('idempotency_key', 'deleted', name='uk_packaging_inspection_idempotency'),
        {'comment': 'Packaging inspection decisions'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    hu_id: Mapped[int] = mapped_column(sa.BigInteger)
    result: Mapped[PackagingInspectionResult] = mapped_column(sa.String(20))
    idempotency_key: Mapped[str] = mapped_column(sa.String(180))
    appearance_passed: Mapped[bool] = mapped_column(default=True, server_default=sa.true())
    quantity_passed: Mapped[bool] = mapped_column(default=True, server_default=sa.true())
    label_passed: Mapped[bool] = mapped_column(default=True, server_default=sa.true())
    inspected_by: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    notes: Mapped[str | None] = mapped_column(UniversalText, default=None)


class PackagingLabelPrint(Base):
    """Label print/reprint audit trail."""

    __tablename__ = 'mes_packaging_label_print'
    __table_args__ = (
        sa.ForeignKeyConstraint(['hu_id'], ['mes_packaging_handling_unit.id'], name='fk_packaging_label_hu'),
        sa.UniqueConstraint('idempotency_key', 'deleted', name='uk_packaging_label_idempotency'),
        {'comment': 'Packaging label print history'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    hu_id: Mapped[int] = mapped_column(sa.BigInteger)
    template_code: Mapped[str] = mapped_column(sa.String(80))
    idempotency_key: Mapped[str] = mapped_column(sa.String(180))
    copies: Mapped[int] = mapped_column(default=1, server_default='1')
    printer_name: Mapped[str | None] = mapped_column(sa.String(120), default=None)
    printed_by: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    reason: Mapped[str | None] = mapped_column(sa.String(500), default=None)
