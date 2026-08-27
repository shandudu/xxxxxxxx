from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, DataClassBase, TimeZone, UniversalText, id_key
from backend.plugin.trace.enums import (
    LotSourceType,
    LotStatus,
    LotType,
    QualityStatus,
    SequenceResetType,
    SerialStatus,
    TraceObjectType,
    TraceRelationType,
    TraceRuleStatus,
    TraceRuleType,
)
from backend.utils.timezone import timezone


class TraceCodeRule(Base):
    """Configurable code rule for MES lots and serial numbers."""

    __tablename__ = 'mes_trace_code_rule'
    __table_args__ = (
        sa.UniqueConstraint('rule_code', name='uk_mes_trace_rule_code'),
        sa.Index('idx_mes_trace_rule_type_status', 'rule_type', 'status'),
        {'comment': 'MES trace code rules'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    rule_code: Mapped[str] = mapped_column(sa.String(50))
    rule_name: Mapped[str] = mapped_column(sa.String(100))
    rule_type: Mapped[TraceRuleType] = mapped_column(sa.String(20))
    pattern: Mapped[str] = mapped_column(sa.String(200))
    sequence_length: Mapped[int] = mapped_column(default=4, server_default='4')
    sequence_reset_type: Mapped[SequenceResetType] = mapped_column(
        sa.String(20), default=SequenceResetType.DAILY, server_default=SequenceResetType.DAILY.value
    )
    prefix: Mapped[str | None] = mapped_column(sa.String(50), default=None)
    status: Mapped[TraceRuleStatus] = mapped_column(
        sa.String(20), default=TraceRuleStatus.ACTIVE, server_default=TraceRuleStatus.ACTIVE.value
    )
    example: Mapped[str | None] = mapped_column(sa.String(200), default=None)
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class MaterialTraceRule(Base):
    """Associates one material with optional lot and serial code rules."""

    __tablename__ = 'mes_material_trace_rule'
    __table_args__ = (
        sa.ForeignKeyConstraint(['material_id'], ['mes_material.id'], name='fk_trace_rule_material'),
        sa.ForeignKeyConstraint(['lot_rule_id'], ['mes_trace_code_rule.id'], name='fk_trace_rule_lot_rule'),
        sa.ForeignKeyConstraint(['serial_rule_id'], ['mes_trace_code_rule.id'], name='fk_trace_rule_serial_rule'),
        sa.UniqueConstraint('material_id', name='uk_mes_material_trace_rule_material'),
        {'comment': 'Material trace code rule assignment'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    material_id: Mapped[int] = mapped_column(sa.BigInteger)
    lot_rule_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    serial_rule_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)


class MaterialLot(Base):
    """A material lot identity; quantity is the original quantity, never inventory balance."""

    __tablename__ = 'mes_material_lot'
    __table_args__ = (
        sa.ForeignKeyConstraint(['material_id'], ['mes_material.id'], name='fk_trace_lot_material'),
        sa.ForeignKeyConstraint(['unit_id'], ['mes_unit.id'], name='fk_trace_lot_unit'),
        sa.ForeignKeyConstraint(['parent_lot_id'], ['mes_material_lot.id'], name='fk_trace_lot_parent'),
        sa.UniqueConstraint('lot_no', name='uk_mes_trace_lot_no'),
        sa.Index('idx_mes_trace_lot_material', 'material_id'),
        sa.Index('idx_mes_trace_lot_status', 'status'),
        sa.Index('idx_mes_trace_lot_parent', 'parent_lot_id'),
        {'comment': 'MES material lots'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    lot_no: Mapped[str] = mapped_column(sa.String(100))
    material_id: Mapped[int] = mapped_column(sa.BigInteger)
    lot_type: Mapped[LotType] = mapped_column(sa.String(30))
    source_type: Mapped[LotSourceType | None] = mapped_column(sa.String(30), default=None)
    source_ref_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    source_ref_no: Mapped[str | None] = mapped_column(sa.String(100), default=None)
    parent_lot_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    production_date: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    expiry_date: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    quantity: Mapped[Decimal | None] = mapped_column(sa.Numeric(18, 6), default=None)
    unit_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    status: Mapped[LotStatus] = mapped_column(
        sa.String(30), default=LotStatus.ACTIVE, server_default=LotStatus.ACTIVE.value
    )
    quality_status: Mapped[QualityStatus] = mapped_column(
        sa.String(30), default=QualityStatus.UNINSPECTED, server_default=QualityStatus.UNINSPECTED.value
    )
    supplier_lot_no: Mapped[str | None] = mapped_column(sa.String(100), default=None)
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)
    created_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)
    updated_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)


class MaterialSerial(Base):
    """An individually traceable material serial number."""

    __tablename__ = 'mes_material_serial'
    __table_args__ = (
        sa.ForeignKeyConstraint(['material_id'], ['mes_material.id'], name='fk_trace_serial_material'),
        sa.ForeignKeyConstraint(['lot_id'], ['mes_material_lot.id'], name='fk_trace_serial_lot'),
        sa.UniqueConstraint('serial_no', name='uk_mes_trace_serial_no'),
        sa.Index('idx_mes_trace_serial_material', 'material_id'),
        sa.Index('idx_mes_trace_serial_lot', 'lot_id'),
        sa.Index('idx_mes_trace_serial_status', 'status'),
        {'comment': 'MES material serial numbers'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    serial_no: Mapped[str] = mapped_column(sa.String(120))
    material_id: Mapped[int] = mapped_column(sa.BigInteger)
    lot_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    source_type: Mapped[LotSourceType | None] = mapped_column(sa.String(30), default=None)
    source_ref_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    source_ref_no: Mapped[str | None] = mapped_column(sa.String(100), default=None)
    status: Mapped[SerialStatus] = mapped_column(
        sa.String(30), default=SerialStatus.ACTIVE, server_default=SerialStatus.ACTIVE.value
    )
    quality_status: Mapped[QualityStatus] = mapped_column(
        sa.String(30), default=QualityStatus.UNINSPECTED, server_default=QualityStatus.UNINSPECTED.value
    )
    production_date: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class TraceRelation(Base):
    """Directed upstream-to-downstream manufacturing genealogy edge."""

    __tablename__ = 'mes_trace_relation'
    __table_args__ = (
        sa.UniqueConstraint(
            'source_type',
            'source_id',
            'target_type',
            'target_id',
            'relation_type',
            'business_ref_key',
            name='uk_mes_trace_relation_business',
        ),
        sa.Index('idx_mes_trace_relation_source', 'source_type', 'source_id'),
        sa.Index('idx_mes_trace_relation_target', 'target_type', 'target_id'),
        sa.Index('idx_mes_trace_relation_source_code', 'source_code'),
        sa.Index('idx_mes_trace_relation_target_code', 'target_code'),
        sa.Index('idx_mes_trace_relation_business_id', 'business_ref_id'),
        {'comment': 'MES lot and serial genealogy relations'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    source_type: Mapped[TraceObjectType] = mapped_column(sa.String(20))
    source_id: Mapped[int] = mapped_column(sa.BigInteger)
    source_code: Mapped[str] = mapped_column(sa.String(120))
    target_type: Mapped[TraceObjectType] = mapped_column(sa.String(20))
    target_id: Mapped[int] = mapped_column(sa.BigInteger)
    target_code: Mapped[str] = mapped_column(sa.String(120))
    relation_type: Mapped[TraceRelationType] = mapped_column(sa.String(30))
    quantity: Mapped[Decimal | None] = mapped_column(sa.Numeric(18, 6), default=None)
    unit_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    operation_ref_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    business_ref_type: Mapped[str | None] = mapped_column(sa.String(30), default=None)
    business_ref_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    business_ref_no: Mapped[str | None] = mapped_column(sa.String(100), default=None)
    business_ref_key: Mapped[str] = mapped_column(sa.String(200), default='', server_default='')
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)
    created_by: Mapped[int | None] = mapped_column(sa.BigInteger, init=False, default=None)


class TraceOperationLog(DataClassBase):
    """Immutable object-level audit log for traceability configuration and genealogy changes."""

    __tablename__ = 'mes_trace_operation_log'
    __table_args__ = (
        sa.Index('idx_mes_trace_operation_object', 'object_type', 'object_id'),
        sa.Index('idx_mes_trace_operation_action', 'action'),
        {'comment': 'MES traceability operation audit log'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    object_type: Mapped[str] = mapped_column(sa.String(30))
    action: Mapped[str] = mapped_column(sa.String(50))
    operator_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    object_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    object_code: Mapped[str | None] = mapped_column(sa.String(120), default=None)
    before_data: Mapped[dict | None] = mapped_column(sa.JSON(), default=None)
    after_data: Mapped[dict | None] = mapped_column(sa.JSON(), default=None)
    created_time: Mapped[datetime] = mapped_column(TimeZone, init=False, default_factory=timezone.now)
    updated_time: Mapped[datetime | None] = mapped_column(TimeZone, init=False, onupdate=timezone.now, default=None)


class TraceCodeSequence(DataClassBase):
    """Database-backed, row-locked counter used to reserve trace code sequences."""

    __tablename__ = 'mes_trace_code_sequence'
    __table_args__ = (
        sa.ForeignKeyConstraint(['rule_id'], ['mes_trace_code_rule.id'], name='fk_trace_sequence_rule'),
        sa.UniqueConstraint('rule_id', 'sequence_key', name='uk_mes_trace_sequence_rule_key'),
        {'comment': 'Trace code sequence counters'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    rule_id: Mapped[int] = mapped_column(sa.BigInteger)
    sequence_key: Mapped[str] = mapped_column(sa.String(32))
    current_value: Mapped[int] = mapped_column(default=0, server_default='0')
    created_time: Mapped[datetime] = mapped_column(TimeZone, init=False, default_factory=timezone.now)
    updated_time: Mapped[datetime | None] = mapped_column(TimeZone, init=False, onupdate=timezone.now, default=None)
