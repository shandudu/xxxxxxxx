from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, UniversalText, id_key
from backend.plugin.quality.enums import (
    InspectionTemplateStatus,
    InspectionType,
    InspectionValueType,
    QualityConfigStatus,
)


class QualityInspectionItem(Base):
    __tablename__ = 'mes_quality_inspection_item'
    __table_args__ = (
        sa.UniqueConstraint('item_code', 'deleted', name='uk_mes_quality_inspection_item_code'),
        {'comment': 'MES quality inspection item definitions'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    item_code: Mapped[str] = mapped_column(sa.String(80))
    item_name: Mapped[str] = mapped_column(sa.String(200))
    value_type: Mapped[InspectionValueType] = mapped_column(sa.String(20))
    unit_label: Mapped[str | None] = mapped_column(sa.String(30), default=None)
    status: Mapped[QualityConfigStatus] = mapped_column(
        sa.String(20), default=QualityConfigStatus.ACTIVE, server_default=QualityConfigStatus.ACTIVE.value,
    )


class QualitySamplingPlan(Base):
    __tablename__ = 'mes_quality_sampling_plan'
    __table_args__ = (
        sa.UniqueConstraint('plan_code', 'deleted', name='uk_mes_quality_sampling_plan_code'),
        {'comment': 'MES quality sampling plans'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    plan_code: Mapped[str] = mapped_column(sa.String(80))
    plan_name: Mapped[str] = mapped_column(sa.String(200))
    sample_size: Mapped[int] = mapped_column()
    acceptance_number: Mapped[int] = mapped_column()
    status: Mapped[QualityConfigStatus] = mapped_column(
        sa.String(20), default=QualityConfigStatus.ACTIVE, server_default=QualityConfigStatus.ACTIVE.value,
    )


class QualityInspectionTemplate(Base):
    __tablename__ = 'mes_quality_inspection_template'
    __table_args__ = (
        sa.ForeignKeyConstraint(['material_id'], ['mes_material.id'], name='fk_quality_template_material'),
        sa.ForeignKeyConstraint(['sampling_plan_id'], ['mes_quality_sampling_plan.id'], name='fk_quality_template_sampling_plan'),
        sa.UniqueConstraint('material_id', 'inspection_type', 'template_version', 'deleted', name='uk_mes_quality_template_version'),
        sa.Index('idx_mes_quality_template_status', 'status'),
        {'comment': 'MES quality inspection templates'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    template_code: Mapped[str] = mapped_column(sa.String(80))
    template_name: Mapped[str] = mapped_column(sa.String(200))
    material_id: Mapped[int] = mapped_column(sa.BigInteger)
    template_version: Mapped[str] = mapped_column(sa.String(30))
    inspection_type: Mapped[InspectionType] = mapped_column(sa.String(30))
    sampling_plan_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None)
    status: Mapped[InspectionTemplateStatus] = mapped_column(
        sa.String(20), default=InspectionTemplateStatus.DRAFT, server_default=InspectionTemplateStatus.DRAFT.value,
    )
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class QualityInspectionStandard(Base):
    __tablename__ = 'mes_quality_inspection_standard'
    __table_args__ = (
        sa.ForeignKeyConstraint(['template_id'], ['mes_quality_inspection_template.id'], name='fk_quality_standard_template'),
        sa.ForeignKeyConstraint(['inspection_item_id'], ['mes_quality_inspection_item.id'], name='fk_quality_standard_item'),
        sa.UniqueConstraint('template_id', 'line_no', 'deleted', name='uk_mes_quality_standard_line'),
        sa.UniqueConstraint('template_id', 'inspection_item_id', 'deleted', name='uk_mes_quality_standard_item'),
        {'comment': 'MES quality inspection standards'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    template_id: Mapped[int] = mapped_column(sa.BigInteger)
    line_no: Mapped[int] = mapped_column()
    inspection_item_id: Mapped[int] = mapped_column(sa.BigInteger)
    lower_limit: Mapped[Decimal | None] = mapped_column(sa.Numeric(18, 6), default=None)
    upper_limit: Mapped[Decimal | None] = mapped_column(sa.Numeric(18, 6), default=None)
    expected_boolean: Mapped[bool | None] = mapped_column(sa.Boolean, default=None)
    expected_text: Mapped[str | None] = mapped_column(sa.String(200), default=None)
    required: Mapped[bool] = mapped_column(sa.Boolean, default=True, server_default=sa.true())
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)


class QualityInspectionResultLine(Base):
    __tablename__ = 'mes_quality_inspection_result'
    __table_args__ = (
        sa.ForeignKeyConstraint(['inspection_id'], ['mes_quality_inspection.id'], name='fk_quality_result_inspection'),
        sa.ForeignKeyConstraint(['template_id'], ['mes_quality_inspection_template.id'], name='fk_quality_result_template'),
        sa.ForeignKeyConstraint(['standard_id'], ['mes_quality_inspection_standard.id'], name='fk_quality_result_standard'),
        sa.ForeignKeyConstraint(['inspection_item_id'], ['mes_quality_inspection_item.id'], name='fk_quality_result_item'),
        sa.UniqueConstraint('inspection_id', 'standard_id', 'deleted', name='uk_mes_quality_result_standard'),
        {'comment': 'MES inspection result lines with standard snapshots'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    inspection_id: Mapped[int] = mapped_column(sa.BigInteger)
    template_id: Mapped[int] = mapped_column(sa.BigInteger)
    standard_id: Mapped[int] = mapped_column(sa.BigInteger)
    inspection_item_id: Mapped[int] = mapped_column(sa.BigInteger)
    line_no_snapshot: Mapped[int] = mapped_column()
    item_code_snapshot: Mapped[str] = mapped_column(sa.String(80))
    item_name_snapshot: Mapped[str] = mapped_column(sa.String(200))
    value_type_snapshot: Mapped[InspectionValueType] = mapped_column(sa.String(20))
    is_qualified: Mapped[bool] = mapped_column(sa.Boolean)
    lower_limit_snapshot: Mapped[Decimal | None] = mapped_column(sa.Numeric(18, 6), default=None)
    upper_limit_snapshot: Mapped[Decimal | None] = mapped_column(sa.Numeric(18, 6), default=None)
    expected_boolean_snapshot: Mapped[bool | None] = mapped_column(sa.Boolean, default=None)
    expected_text_snapshot: Mapped[str | None] = mapped_column(sa.String(200), default=None)
    numeric_value: Mapped[Decimal | None] = mapped_column(sa.Numeric(18, 6), default=None)
    boolean_value: Mapped[bool | None] = mapped_column(sa.Boolean, default=None)
    text_value: Mapped[str | None] = mapped_column(sa.String(500), default=None)
    remark: Mapped[str | None] = mapped_column(UniversalText, default=None)
