from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, TimeZone, UniversalText, id_key


class SalesOrderPromiseAssessment(Base):
    """Traceable ATP/CTP assessment for one sales-order line."""

    __tablename__ = 'erp_sales_order_promise_assessment'
    __table_args__ = (
        sa.ForeignKeyConstraint(['sales_order_id'], ['erp_sales_order.id'], name='fk_promise_order'),
        sa.ForeignKeyConstraint(['sales_order_line_id'], ['erp_sales_order_line.id'], name='fk_promise_order_line'),
        sa.ForeignKeyConstraint(['material_id'], ['mes_material.id'], name='fk_promise_material'),
        sa.UniqueConstraint('sales_order_line_id', 'deleted', name='uk_promise_order_line'),
        sa.Index('idx_promise_risk_status', 'risk_status', 'requested_delivery_at'),
        sa.Index('idx_promise_material_date', 'material_id', 'requested_delivery_at'),
        {'comment': 'ERP sales order ATP/CTP promise assessments'},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    sales_order_id: Mapped[int] = mapped_column(sa.BigInteger)
    sales_order_line_id: Mapped[int] = mapped_column(sa.BigInteger)
    material_id: Mapped[int] = mapped_column(sa.BigInteger)
    requested_delivery_at: Mapped[datetime] = mapped_column(TimeZone)
    assessed_at: Mapped[datetime] = mapped_column(TimeZone)
    ordered_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    shipped_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    atp_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    open_purchase_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    open_production_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    ctp_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    shortage_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    capacity_shortage_quantity: Mapped[Decimal] = mapped_column(sa.Numeric(18, 6))
    risk_status: Mapped[str] = mapped_column(sa.String(30))
    promised_delivery_at: Mapped[datetime | None] = mapped_column(TimeZone, default=None)
    risk_notes: Mapped[str | None] = mapped_column(UniversalText, default=None)
