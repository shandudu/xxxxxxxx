from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP

import sqlalchemy as sa
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette_context.errors import ContextDoesNotExistError

from backend.app.admin.model.user import User
from backend.common.context import ctx
from backend.common.exception import errors
from backend.plugin.costing.model import CostPeriod, WorkOrderCost
from backend.plugin.costing.enums import MarginDimension
from backend.plugin.costing.service import costing_service
from backend.plugin.customer.model import Customer
from backend.plugin.finance.enums import BankDirection, BankStatementStatus, BudgetAlertStatus, BudgetStatus, ClosingCheckStatus, ExpenseClaimStatus, FinancePeriodStatus, FixedAssetCountApprovalStatus, FixedAssetCountStatus, FixedAssetCountVariance, FixedAssetStatus, FixedAssetTransactionType, InventoryCountStatus, PaymentPlanDirection, PaymentPlanStatus, TaxInvoiceDirection, TaxInvoiceStatus, ThreeWayMatchStatus, VoucherSourceType, VoucherStatus
from backend.plugin.finance.model import APInvoice, APPayment, ARInvoice, ARReceipt, BankReconciliation, BankStatement, BudgetAlert, CashFlowForecast, CostCenter, ExpenseClaim, ExpenseClaimLine, FinanceBudget, FinanceBudgetLine, FinanceClosingCheck, FinancePeriod, FixedAsset, FixedAssetCountLine, FixedAssetCountTask, FixedAssetDepreciation, FixedAssetMaintenance, FixedAssetTaxDepreciation, FixedAssetTransaction, GLVoucher, GLVoucherLine, InventoryCountLine, InventoryCountTask, InventoryValuation, PaymentPlan, TaxInvoiceLedger, ThreeWayMatch
from backend.plugin.finance.schema.finance import APInvoiceCreate, ARInvoiceCreate, AutoInvoiceRequest, BankReconcileRequest, BankStatementCreate, BudgetCreate, BudgetDetail, BudgetAlertDetail, FinancePeriodCreate, FinanceDashboard, CostCenterCreate, CostCenterDetail, ExpenseClaimCreate, ExpenseClaimDetail, FixedAssetCountApprovalRequest, FixedAssetCountCreate, FixedAssetCountDetail, FixedAssetCountLineDetail, FixedAssetCountScanRequest, FixedAssetCountScanResult, FixedAssetCreate, FixedAssetDetail, FixedAssetDepreciationDetail, FixedAssetDepreciationSummary, FixedAssetDisposeRequest, FixedAssetDualDepreciationDetail, FixedAssetDualDepreciationSummary, FixedAssetFromReceiptRequest, FixedAssetMaintenanceCreate, FixedAssetMaintenanceDetail, FixedAssetTransferRequest, InventoryCountCreate, InventoryCountDetail, InventoryValuationDetail, SettlementCreate, TaxInvoiceDetail, TaxInvoiceSyncRequest, CashFlowForecastSummary, CashFlowForecastRow, ClosingCheckDetail, ThreeWayMatchDetail, ThreeWayMatchRequest, VoucherDetail, VoucherGenerateRequest
from backend.plugin.inventory.enums import StockTransactionType
from backend.plugin.inventory.model import InventoryBalance, StockTransaction
from backend.plugin.inventory.schema.inventory import StockAdjustmentConfig
from backend.plugin.inventory.service import inventory_service
from backend.plugin.material.model import Material
from backend.plugin.purchasing.model import PurchaseOrderLine, SupplierReceiptLine
from backend.plugin.purchasing.model import PurchaseOrder, SupplierReceipt
from backend.plugin.sales.model import SalesOrderLine, Shipment, ShipmentLine
from backend.plugin.supplier.model import Supplier
from backend.utils.timezone import timezone

MONEY = Decimal('0.000001')


def money(value: Decimal | int | float | None) -> Decimal:
    return Decimal(value or 0).quantize(MONEY, rounding=ROUND_HALF_UP)


class FinanceService:
    @staticmethod
    def _operator_id() -> int | None:
        try:
            return ctx.user_id
        except (AttributeError, ContextDoesNotExistError, LookupError):
            return None

    @staticmethod
    async def create_period(db: AsyncSession, obj: FinancePeriodCreate) -> FinancePeriod:
        if await db.scalar(select(FinancePeriod).where(FinancePeriod.period_code == obj.period_code, FinancePeriod.deleted == 0)):
            raise errors.RequestError(msg='FINANCE_PERIOD_ALREADY_EXISTS')
        period = FinancePeriod(**obj.model_dump())
        db.add(period)
        await db.flush()
        return period

    @staticmethod
    async def periods(db: AsyncSession) -> list[FinancePeriod]:
        return list((await db.scalars(select(FinancePeriod).where(FinancePeriod.deleted == 0).order_by(FinancePeriod.start_date.desc()))).all())

    @staticmethod
    async def _period(db: AsyncSession, period_id: int) -> FinancePeriod:
        period = await db.scalar(select(FinancePeriod).where(FinancePeriod.id == period_id, FinancePeriod.deleted == 0))
        if not period:
            raise errors.NotFoundError(msg='FINANCE_PERIOD_NOT_FOUND')
        return period

    @staticmethod
    async def closing_checks(db: AsyncSession, period_id: int) -> list[ClosingCheckDetail]:
        period = await FinanceService._period(db, period_id)
        start_at, end_at = FinanceService._boundaries(period)
        checks: list[tuple[str, str, bool, bool, str]] = []
        valuation_count = int(await db.scalar(select(func.count(InventoryValuation.id)).where(InventoryValuation.period_id == period_id, InventoryValuation.deleted == 0)) or 0)
        checks.append(('INVENTORY_VALUATION', '库存计价已计算', True, valuation_count > 0, f'valuation_rows={valuation_count}'))
        active_counts = int(await db.scalar(select(func.count(InventoryCountTask.id)).where(InventoryCountTask.period_id == period_id, InventoryCountTask.status.in_([InventoryCountStatus.DRAFT, InventoryCountStatus.COUNTING]), InventoryCountTask.deleted == 0)) or 0)
        checks.append(('INVENTORY_COUNT', '盘点任务已完成过账', True, active_counts == 0, f'open_count_tasks={active_counts}'))
        unbalanced = int(await db.scalar(select(func.count(GLVoucher.id)).where(GLVoucher.period_id == period_id, GLVoucher.deleted == 0, GLVoucher.total_debit != GLVoucher.total_credit)) or 0)
        checks.append(('VOUCHER_BALANCE', '凭证借贷平衡', True, unbalanced == 0, f'unbalanced_vouchers={unbalanced}'))
        unmatched = int(await db.scalar(select(func.count(BankStatement.id)).where(BankStatement.transaction_date >= period.start_date, BankStatement.transaction_date <= period.end_date, BankStatement.status.in_([BankStatementStatus.UNMATCHED, BankStatementStatus.PARTIAL]), BankStatement.deleted == 0)) or 0)
        checks.append(('BANK_RECONCILIATION', '银行流水已对账', False, unmatched == 0, f'unmatched_statements={unmatched}'))
        now = timezone.now()
        result: list[ClosingCheckDetail] = []
        for code, name, blocking, passed, detail in checks:
            row = await db.scalar(select(FinanceClosingCheck).where(FinanceClosingCheck.period_id == period_id, FinanceClosingCheck.check_code == code, FinanceClosingCheck.deleted == 0))
            if not row:
                row = FinanceClosingCheck(period_id=period_id, check_code=code, check_name=name, status=ClosingCheckStatus.PASS if passed else ClosingCheckStatus.BLOCK, checked_at=now, blocking=blocking, detail=detail)
                db.add(row)
            else:
                row.status = ClosingCheckStatus.PASS if passed else ClosingCheckStatus.BLOCK; row.checked_at = now; row.blocking = blocking; row.detail = detail
            await db.flush(); result.append(ClosingCheckDetail.model_validate(row))
        return result

    @staticmethod
    async def close_period(db: AsyncSession, period_id: int) -> FinancePeriod:
        period = await FinanceService._period(db, period_id)
        if period.status == FinancePeriodStatus.CLOSED:
            return period
        checks = await FinanceService.closing_checks(db, period_id)
        if any(row.blocking and row.status == ClosingCheckStatus.BLOCK for row in checks):
            raise errors.RequestError(msg='FINANCE_CLOSING_BLOCKED')
        period.status = FinancePeriodStatus.CLOSED; period.closed_at = timezone.now(); await db.flush(); return period

    @staticmethod
    async def create_inventory_count(db: AsyncSession, obj: InventoryCountCreate) -> InventoryCountDetail:
        period = await FinanceService._period(db, obj.period_id)
        if period.status == FinancePeriodStatus.CLOSED: raise errors.RequestError(msg='FINANCE_PERIOD_CLOSED')
        task = InventoryCountTask(task_no=f'IC-{period.period_code.replace("-", "")}-{timezone.now():%H%M%S%f}', period_id=period.id, warehouse_id=obj.warehouse_id, status=InventoryCountStatus.COUNTING, counted_at=timezone.now(), remark=obj.remark)
        db.add(task); await db.flush()
        for item in obj.lines:
            filters = [InventoryBalance.material_id == item.material_id, InventoryBalance.warehouse_id == item.warehouse_id, InventoryBalance.location_id == item.location_id, InventoryBalance.deleted == 0]
            filters.append(InventoryBalance.lot_id.is_(None) if item.lot_id is None else InventoryBalance.lot_id == item.lot_id)
            balance = await db.scalar(select(InventoryBalance).where(*filters))
            book = money(balance.quantity if balance else 0); variance = money(item.counted_quantity - book)
            valuation = await db.scalar(select(InventoryValuation).where(InventoryValuation.period_id == period.id, InventoryValuation.material_id == item.material_id, InventoryValuation.deleted == 0).order_by(InventoryValuation.id.desc()))
            unit_cost = money(valuation.unit_cost if valuation else 0)
            db.add(InventoryCountLine(task_id=task.id, material_id=item.material_id, warehouse_id=item.warehouse_id, location_id=item.location_id, lot_id=item.lot_id, book_quantity=book, counted_quantity=item.counted_quantity, variance_quantity=variance, unit_cost=unit_cost, variance_value=money(variance * unit_cost), remark=item.remark))
        await db.flush(); return await FinanceService.inventory_count_detail(db, task.id)

    @staticmethod
    async def inventory_count_detail(db: AsyncSession, task_id: int) -> InventoryCountDetail:
        task = await db.scalar(select(InventoryCountTask).where(InventoryCountTask.id == task_id, InventoryCountTask.deleted == 0))
        if not task: raise errors.NotFoundError(msg='INVENTORY_COUNT_NOT_FOUND')
        lines = list((await db.scalars(select(InventoryCountLine).where(InventoryCountLine.task_id == task.id, InventoryCountLine.deleted == 0).order_by(InventoryCountLine.id))).all())
        return InventoryCountDetail.model_validate({**{k: getattr(task, k) for k in ('id','task_no','period_id','warehouse_id','status','counted_at','posted_at','remark')}, 'lines': lines})

    @staticmethod
    async def post_inventory_count(db: AsyncSession, task_id: int) -> InventoryCountDetail:
        task = await db.scalar(select(InventoryCountTask).where(InventoryCountTask.id == task_id, InventoryCountTask.deleted == 0))
        if not task: raise errors.NotFoundError(msg='INVENTORY_COUNT_NOT_FOUND')
        if task.status == InventoryCountStatus.POSTED: return await FinanceService.inventory_count_detail(db, task_id)
        for line in (await db.scalars(select(InventoryCountLine).where(InventoryCountLine.task_id == task.id, InventoryCountLine.deleted == 0))).all():
            if line.variance_quantity == 0: continue
            tx = await inventory_service.post_adjustment(db, StockAdjustmentConfig(idempotency_key=f'COUNT:{task.id}:{line.id}', material_id=line.material_id, lot_id=line.lot_id, warehouse_id=line.warehouse_id, location_id=line.location_id, quantity_delta=line.variance_quantity, reference_no=task.task_no, remark='库存盘点差异'))
            line.adjustment_transaction_id = tx.id
        task.status = InventoryCountStatus.POSTED; task.posted_at = timezone.now(); await db.flush(); return await FinanceService.inventory_count_detail(db, task_id)

    @staticmethod
    async def sync_tax_invoices(db: AsyncSession, obj: TaxInvoiceSyncRequest) -> list[TaxInvoiceDetail]:
        period = await FinanceService._period(db, obj.period_id); result: list[TaxInvoiceDetail] = []
        ars = (await db.scalars(select(ARInvoice).where(ARInvoice.invoice_date >= period.start_date, ARInvoice.invoice_date <= period.end_date, ARInvoice.deleted == 0))).all()
        aps = (await db.scalars(select(APInvoice).where(APInvoice.invoice_date >= period.start_date, APInvoice.invoice_date <= period.end_date, APInvoice.deleted == 0))).all()
        for invoice, direction in [*((row, TaxInvoiceDirection.OUTPUT) for row in ars), *((row, TaxInvoiceDirection.INPUT) for row in aps)]:
            is_ar = direction == TaxInvoiceDirection.OUTPUT; no = invoice.invoice_no
            row = await db.scalar(select(TaxInvoiceLedger).where(TaxInvoiceLedger.invoice_no == no, TaxInvoiceLedger.deleted == 0))
            tax_rate = money(invoice.tax_amount / invoice.net_amount * 100) if invoice.net_amount else Decimal('0')
            payload = dict(invoice_no=no, direction=direction, partner_id=invoice.customer_id if is_ar else invoice.supplier_id, partner_name_snapshot=invoice.customer_name_snapshot if is_ar else invoice.supplier_name_snapshot, issue_date=invoice.invoice_date, tax_rate=tax_rate, net_amount=invoice.net_amount, tax_amount=invoice.tax_amount, total_amount=invoice.total_amount, ar_invoice_id=invoice.id if is_ar else None, ap_invoice_id=invoice.id if not is_ar else None)
            if not row: row = TaxInvoiceLedger(**payload); db.add(row)
            else:
                for key, value in payload.items(): setattr(row, key, value)
            await db.flush(); result.append(TaxInvoiceDetail.model_validate(row))
        return result

    @staticmethod
    async def cash_flow_forecast(db: AsyncSession, period_id: int, rebuild: bool = False) -> CashFlowForecastSummary:
        period = await FinanceService._period(db, period_id)
        if rebuild:
            old = (await db.scalars(select(CashFlowForecast).where(CashFlowForecast.period_id == period_id, CashFlowForecast.deleted == 0))).all()
            for row in old: row.deleted = 1; row.deleted_time = timezone.now()
            plans = (await db.scalars(select(PaymentPlan).where(PaymentPlan.deleted == 0, PaymentPlan.status != PaymentPlanStatus.SETTLED, PaymentPlan.due_date >= period.start_date, PaymentPlan.due_date <= period.end_date))).all()
            for plan in plans:
                db.add(CashFlowForecast(period_id=period.id, forecast_date=plan.due_date, direction='IN' if plan.direction == PaymentPlanDirection.AR else 'OUT', category='AR' if plan.direction == PaymentPlanDirection.AR else 'AP', source_type='PAYMENT_PLAN', source_id=plan.id, partner_name_snapshot=plan.partner_name_snapshot, expected_amount=money(plan.planned_amount - plan.settled_amount), confidence=Decimal('100')))
            await db.flush()
        rows = list((await db.scalars(select(CashFlowForecast).where(CashFlowForecast.period_id == period_id, CashFlowForecast.deleted == 0).order_by(CashFlowForecast.forecast_date, CashFlowForecast.id))).all())
        inflow = money(sum((row.expected_amount for row in rows if row.direction == 'IN'), Decimal('0'))); outflow = money(sum((row.expected_amount for row in rows if row.direction == 'OUT'), Decimal('0')))
        return CashFlowForecastSummary(period_id=period_id, inflow=inflow, outflow=outflow, net_cash_flow=money(inflow - outflow), rows=[CashFlowForecastRow.model_validate(row) for row in rows])

    @staticmethod
    async def create_cost_center(db: AsyncSession, obj: CostCenterCreate) -> CostCenter:
        if await db.scalar(select(CostCenter).where(CostCenter.center_code == obj.center_code, CostCenter.deleted == 0)):
            raise errors.RequestError(msg='COST_CENTER_ALREADY_EXISTS')
        if obj.parent_id and not await db.scalar(select(CostCenter).where(CostCenter.id == obj.parent_id, CostCenter.deleted == 0)):
            raise errors.NotFoundError(msg='PARENT_COST_CENTER_NOT_FOUND')
        row = CostCenter(**obj.model_dump()); db.add(row); await db.flush(); return row

    @staticmethod
    async def cost_centers(db: AsyncSession) -> list[CostCenterDetail]:
        rows = (await db.scalars(select(CostCenter).where(CostCenter.deleted == 0).order_by(CostCenter.center_code))).all()
        return [CostCenterDetail.model_validate(row) for row in rows]

    @staticmethod
    async def budget_detail(db: AsyncSession, budget_id: int) -> BudgetDetail:
        budget = await db.scalar(select(FinanceBudget).where(FinanceBudget.id == budget_id, FinanceBudget.deleted == 0))
        if not budget: raise errors.NotFoundError(msg='BUDGET_NOT_FOUND')
        lines = (await db.scalars(select(FinanceBudgetLine).where(FinanceBudgetLine.budget_id == budget.id, FinanceBudgetLine.deleted == 0).order_by(FinanceBudgetLine.id))).all()
        return BudgetDetail.model_validate({**{key: getattr(budget, key) for key in ('id','budget_no','period_id','budget_name','budget_type','total_amount','cost_center_id','status','approved_at','remark')}, 'lines': lines})

    @staticmethod
    async def create_budget(db: AsyncSession, obj: BudgetCreate) -> BudgetDetail:
        period = await FinanceService._period(db, obj.period_id)
        if period.status == FinancePeriodStatus.CLOSED: raise errors.RequestError(msg='FINANCE_PERIOD_CLOSED')
        if obj.cost_center_id and not await db.scalar(select(CostCenter).where(CostCenter.id == obj.cost_center_id, CostCenter.status == 'ACTIVE', CostCenter.deleted == 0)):
            raise errors.NotFoundError(msg='COST_CENTER_NOT_FOUND')
        budget_no = f'BG-{period.period_code.replace("-", "")}-{timezone.now():%H%M%S%f}'
        total = money(sum((line.budget_amount for line in obj.lines), Decimal('0')))
        budget = FinanceBudget(budget_no=budget_no, period_id=period.id, budget_name=obj.budget_name, budget_type=obj.budget_type, total_amount=total, cost_center_id=obj.cost_center_id, remark=obj.remark)
        db.add(budget); await db.flush()
        for line in obj.lines:
            db.add(FinanceBudgetLine(budget_id=budget.id, account_code=line.account_code, category=line.category, budget_amount=line.budget_amount, warning_threshold=line.warning_threshold, remark=line.remark))
        await db.flush(); return await FinanceService.budget_detail(db, budget.id)

    @staticmethod
    async def budgets(db: AsyncSession, period_id: int | None = None) -> list[BudgetDetail]:
        filters = [FinanceBudget.deleted == 0]
        if period_id: filters.append(FinanceBudget.period_id == period_id)
        rows = (await db.scalars(select(FinanceBudget).where(*filters).order_by(FinanceBudget.id.desc()))).all()
        return [await FinanceService.budget_detail(db, row.id) for row in rows]

    @staticmethod
    async def approve_budget(db: AsyncSession, budget_id: int) -> BudgetDetail:
        budget = await db.scalar(select(FinanceBudget).where(FinanceBudget.id == budget_id, FinanceBudget.deleted == 0))
        if not budget: raise errors.NotFoundError(msg='BUDGET_NOT_FOUND')
        period = await FinanceService._period(db, budget.period_id)
        if period.status == FinancePeriodStatus.CLOSED: raise errors.RequestError(msg='FINANCE_PERIOD_CLOSED')
        budget.status = BudgetStatus.APPROVED; budget.approved_at = timezone.now(); await db.flush(); return await FinanceService.budget_detail(db, budget.id)

    @staticmethod
    async def create_expense_claim(db: AsyncSession, obj: ExpenseClaimCreate) -> ExpenseClaimDetail:
        period = await FinanceService._period(db, obj.period_id)
        if period.status == FinancePeriodStatus.CLOSED: raise errors.RequestError(msg='FINANCE_PERIOD_CLOSED')
        if obj.cost_center_id and not await db.scalar(select(CostCenter).where(CostCenter.id == obj.cost_center_id, CostCenter.deleted == 0)):
            raise errors.NotFoundError(msg='COST_CENTER_NOT_FOUND')
        total = money(sum((line.amount + line.tax_amount for line in obj.lines), Decimal('0')))
        claim = ExpenseClaim(claim_no=f'EXP-{period.period_code.replace("-", "")}-{timezone.now():%H%M%S%f}', period_id=period.id, applicant_id=obj.applicant_id, expense_date=obj.expense_date, cost_center_id=obj.cost_center_id, total_amount=total, status=ExpenseClaimStatus.SUBMITTED, description=obj.description)
        db.add(claim); await db.flush()
        for line in obj.lines:
            if line.budget_line_id:
                budget_line = await db.scalar(select(FinanceBudgetLine).join(FinanceBudget, FinanceBudget.id == FinanceBudgetLine.budget_id).where(FinanceBudgetLine.id == line.budget_line_id, FinanceBudgetLine.deleted == 0, FinanceBudget.deleted == 0, FinanceBudget.status == BudgetStatus.APPROVED))
                if not budget_line: raise errors.RequestError(msg='APPROVED_BUDGET_LINE_NOT_FOUND')
            else:
                raise errors.RequestError(msg='EXPENSE_BUDGET_LINE_REQUIRED')
            db.add(ExpenseClaimLine(claim_id=claim.id, category=line.category, amount=line.amount, tax_amount=line.tax_amount, budget_line_id=line.budget_line_id, description=line.description, invoice_no=line.invoice_no))
        await db.flush(); return await FinanceService.expense_claim_detail(db, claim.id)

    @staticmethod
    async def expense_claim_detail(db: AsyncSession, claim_id: int) -> ExpenseClaimDetail:
        claim = await db.scalar(select(ExpenseClaim).where(ExpenseClaim.id == claim_id, ExpenseClaim.deleted == 0))
        if not claim: raise errors.NotFoundError(msg='EXPENSE_CLAIM_NOT_FOUND')
        lines = (await db.scalars(select(ExpenseClaimLine).where(ExpenseClaimLine.claim_id == claim.id, ExpenseClaimLine.deleted == 0).order_by(ExpenseClaimLine.id))).all()
        return ExpenseClaimDetail.model_validate({**{key: getattr(claim, key) for key in ('id','claim_no','period_id','applicant_id','expense_date','total_amount','cost_center_id','status','description','approved_at','paid_at','voucher_id')}, 'lines': lines})

    @staticmethod
    async def approve_expense_claim(db: AsyncSession, claim_id: int) -> ExpenseClaimDetail:
        claim = await db.scalar(select(ExpenseClaim).where(ExpenseClaim.id == claim_id, ExpenseClaim.deleted == 0))
        if not claim: raise errors.NotFoundError(msg='EXPENSE_CLAIM_NOT_FOUND')
        if claim.status == ExpenseClaimStatus.APPROVED or claim.status == ExpenseClaimStatus.PAID: return await FinanceService.expense_claim_detail(db, claim.id)
        if claim.status != ExpenseClaimStatus.SUBMITTED: raise errors.RequestError(msg='EXPENSE_CLAIM_NOT_SUBMITTED')
        lines = (await db.scalars(select(ExpenseClaimLine).where(ExpenseClaimLine.claim_id == claim.id, ExpenseClaimLine.deleted == 0))).all()
        for line in lines:
            budget_line = await db.scalar(select(FinanceBudgetLine).where(FinanceBudgetLine.id == line.budget_line_id, FinanceBudgetLine.deleted == 0))
            if not budget_line: raise errors.RequestError(msg='BUDGET_LINE_NOT_FOUND')
            spend = money(line.amount + line.tax_amount); available = money(budget_line.budget_amount - budget_line.consumed_amount)
            if spend > available: raise errors.RequestError(msg='BUDGET_EXCEEDED')
            budget_line.consumed_amount = money(budget_line.consumed_amount + spend)
            utilization = money(budget_line.consumed_amount / budget_line.budget_amount * 100) if budget_line.budget_amount else Decimal('100')
            if utilization >= budget_line.warning_threshold:
                alert = await db.scalar(select(BudgetAlert).where(BudgetAlert.budget_line_id == budget_line.id, BudgetAlert.alert_type == ('OVER' if utilization >= 100 else 'WARNING'), BudgetAlert.status == BudgetAlertStatus.OPEN, BudgetAlert.deleted == 0))
                if not alert:
                    db.add(BudgetAlert(budget_line_id=budget_line.id, alert_type='OVER' if utilization >= 100 else 'WARNING', threshold=budget_line.warning_threshold, budget_amount=budget_line.budget_amount, consumed_amount=budget_line.consumed_amount, utilization_rate=utilization, triggered_at=timezone.now(), detail=f'预算执行率 {utilization}%'))
        period = await FinanceService._period(db, claim.period_id)
        voucher = GLVoucher(voucher_no=f'V-EXP-{claim.claim_no}', period_id=period.id, voucher_date=claim.expense_date, source_type='EXPENSE_CLAIM', source_id=claim.id, summary=f'费用报销 {claim.claim_no}', total_debit=claim.total_amount, total_credit=claim.total_amount, status=VoucherStatus.POSTED, posted_at=timezone.now())
        db.add(voucher); await db.flush()
        db.add_all([GLVoucherLine(voucher_id=voucher.id, line_no=1, account_code='6602', account_name='管理费用', debit=claim.total_amount, credit=Decimal('0'), description=claim.description), GLVoucherLine(voucher_id=voucher.id, line_no=2, account_code='2241', account_name='应付职工薪酬-报销', debit=Decimal('0'), credit=claim.total_amount, description=claim.description)])
        claim.status = ExpenseClaimStatus.APPROVED; claim.approved_at = timezone.now(); claim.voucher_id = voucher.id; await db.flush(); return await FinanceService.expense_claim_detail(db, claim.id)

    @staticmethod
    async def reject_expense_claim(db: AsyncSession, claim_id: int, reason: str | None = None) -> ExpenseClaimDetail:
        claim = await db.scalar(select(ExpenseClaim).where(ExpenseClaim.id == claim_id, ExpenseClaim.deleted == 0))
        if not claim: raise errors.NotFoundError(msg='EXPENSE_CLAIM_NOT_FOUND')
        if claim.status not in (ExpenseClaimStatus.SUBMITTED, ExpenseClaimStatus.DRAFT): raise errors.RequestError(msg='EXPENSE_CLAIM_NOT_REJECTABLE')
        claim.status = ExpenseClaimStatus.REJECTED; claim.rejection_reason = reason; await db.flush(); return await FinanceService.expense_claim_detail(db, claim.id)

    @staticmethod
    async def mark_expense_paid(db: AsyncSession, claim_id: int) -> ExpenseClaimDetail:
        claim = await db.scalar(select(ExpenseClaim).where(ExpenseClaim.id == claim_id, ExpenseClaim.deleted == 0))
        if not claim: raise errors.NotFoundError(msg='EXPENSE_CLAIM_NOT_FOUND')
        if claim.status == ExpenseClaimStatus.PAID: return await FinanceService.expense_claim_detail(db, claim.id)
        if claim.status != ExpenseClaimStatus.APPROVED: raise errors.RequestError(msg='EXPENSE_CLAIM_NOT_APPROVED')
        claim.status = ExpenseClaimStatus.PAID; claim.paid_at = timezone.now(); await db.flush(); return await FinanceService.expense_claim_detail(db, claim.id)

    @staticmethod
    async def _fixed_asset(db: AsyncSession, asset_id: int) -> FixedAsset:
        asset = await db.scalar(select(FixedAsset).where(FixedAsset.id == asset_id, FixedAsset.deleted == 0))
        if not asset: raise errors.NotFoundError(msg='FIXED_ASSET_NOT_FOUND')
        return asset

    @staticmethod
    async def _fixed_asset_detail(db: AsyncSession, asset_id: int) -> FixedAssetDetail:
        asset = await FinanceService._fixed_asset(db, asset_id)
        return FixedAssetDetail.model_validate(asset)

    @staticmethod
    async def _fixed_asset_voucher(db: AsyncSession, period: FinancePeriod, source_type: str, source_id: int, amount: Decimal, debit_account: str, debit_name: str, credit_account: str, credit_name: str, summary: str, voucher_date: date) -> GLVoucher:
        existing = await db.scalar(select(GLVoucher).where(GLVoucher.source_type == source_type, GLVoucher.source_id == source_id, GLVoucher.deleted == 0))
        if existing: return existing
        voucher = GLVoucher(voucher_no=f'V-{source_type[:6]}-{period.period_code.replace("-", "")}-{timezone.now():%H%M%S%f}', period_id=period.id, voucher_date=voucher_date, source_type=source_type, source_id=source_id, summary=summary, total_debit=money(amount), total_credit=money(amount), status=VoucherStatus.POSTED, posted_at=timezone.now())
        db.add(voucher); await db.flush()
        db.add_all([GLVoucherLine(voucher_id=voucher.id, line_no=1, account_code=debit_account, account_name=debit_name, debit=money(amount), credit=Decimal('0'), description=summary), GLVoucherLine(voucher_id=voucher.id, line_no=2, account_code=credit_account, account_name=credit_name, debit=Decimal('0'), credit=money(amount), description=summary)])
        await db.flush(); return voucher

    @staticmethod
    async def create_fixed_asset(db: AsyncSession, obj: FixedAssetCreate) -> FixedAssetDetail:
        period = await FinanceService._period(db, obj.period_id)
        if period.status == FinancePeriodStatus.CLOSED: raise errors.RequestError(msg='FINANCE_PERIOD_CLOSED')
        if obj.cost_center_id and not await db.scalar(select(CostCenter).where(CostCenter.id == obj.cost_center_id, CostCenter.status == 'ACTIVE', CostCenter.deleted == 0)):
            raise errors.NotFoundError(msg='COST_CENTER_NOT_FOUND')
        residual = money(obj.original_value * obj.residual_rate / Decimal('100'))
        asset = FixedAsset(asset_no=f'FA-{timezone.now():%Y%m%d%H%M%S%f}', asset_name=obj.asset_name, category=obj.category, period_id=period.id, acquisition_date=obj.acquisition_date, original_value=obj.original_value, useful_life_months=obj.useful_life_months, cost_center_id=obj.cost_center_id, barcode=obj.barcode, serial_number=obj.serial_number, residual_rate=obj.residual_rate, residual_value=residual, accumulated_depreciation=Decimal('0'), net_value=obj.original_value, tax_accumulated_depreciation=Decimal('0'), tax_net_value=obj.original_value, supplier_id=obj.supplier_id, source_type=obj.source_type, source_id=obj.source_id, remark=obj.remark)
        db.add(asset); await db.flush()
        voucher = await FinanceService._fixed_asset_voucher(db, period, 'FIXED_ASSET_ACQUISITION', asset.id, asset.original_value, '1601', '固定资产', '2202', '应付账款', f'固定资产购置 {asset.asset_name}', asset.acquisition_date)
        asset.voucher_id = voucher.id
        db.add(FixedAssetTransaction(asset_id=asset.id, transaction_type=FixedAssetTransactionType.ACQUISITION, transaction_date=asset.acquisition_date, amount=asset.original_value, to_cost_center_id=asset.cost_center_id, voucher_id=voucher.id, description='固定资产购置入账'))
        await db.flush(); return await FinanceService._fixed_asset_detail(db, asset.id)

    @staticmethod
    async def create_fixed_asset_from_receipt(db: AsyncSession, receipt_id: int, obj: FixedAssetFromReceiptRequest) -> FixedAssetDetail:
        receipt = await db.scalar(select(SupplierReceipt).where(SupplierReceipt.id == receipt_id, SupplierReceipt.deleted == 0))
        if not receipt: raise errors.NotFoundError(msg='SUPPLIER_RECEIPT_NOT_FOUND')
        existing = await db.scalar(select(FixedAsset).where(FixedAsset.source_type == 'SUPPLIER_RECEIPT', FixedAsset.source_id == receipt.id, FixedAsset.deleted == 0))
        if existing: return await FinanceService._fixed_asset_detail(db, existing.id)
        lines = list((await db.scalars(select(SupplierReceiptLine).where(SupplierReceiptLine.supplier_receipt_id == receipt.id, SupplierReceiptLine.deleted == 0).order_by(SupplierReceiptLine.id))).all())
        if not lines: raise errors.RequestError(msg='SUPPLIER_RECEIPT_LINE_REQUIRED')
        receipt_line = lines[0]
        ap = await FinanceService.auto_ap_invoice(db, receipt.id, AutoInvoiceRequest(invoice_date=obj.invoice_date, due_date=obj.due_date, tax_rate=obj.tax_rate, invoice_no=obj.invoice_no))
        match = await FinanceService.match_three_way(db, ThreeWayMatchRequest(ap_invoice_id=ap.id, purchase_order_line_id=receipt_line.purchase_order_line_id, supplier_receipt_line_id=receipt_line.id))
        if match.status != ThreeWayMatchStatus.MATCHED:
            raise errors.RequestError(msg='FIXED_ASSET_THREE_WAY_MATCH_FAILED')
        asset = await FinanceService.create_fixed_asset(db, FixedAssetCreate(period_id=obj.period_id, asset_name=obj.asset_name, category=obj.category, acquisition_date=obj.invoice_date, original_value=ap.net_amount, useful_life_months=obj.useful_life_months, residual_rate=obj.residual_rate, cost_center_id=obj.cost_center_id, supplier_id=receipt.supplier_id, source_type='SUPPLIER_RECEIPT', source_id=receipt.id, remark=obj.remark))
        row = await FinanceService._fixed_asset(db, asset.id); row.ap_invoice_id = ap.id; await db.flush()
        return await FinanceService._fixed_asset_detail(db, row.id)

    @staticmethod
    async def fixed_assets(db: AsyncSession, status: str | None = None) -> list[FixedAssetDetail]:
        query = select(FixedAsset).where(FixedAsset.deleted == 0)
        if status: query = query.where(FixedAsset.status == status)
        rows = (await db.scalars(query.order_by(FixedAsset.id.desc()))).all()
        return [FixedAssetDetail.model_validate(row) for row in rows]

    @staticmethod
    async def transfer_fixed_asset(db: AsyncSession, asset_id: int, obj: FixedAssetTransferRequest) -> FixedAssetDetail:
        asset = await FinanceService._fixed_asset(db, asset_id)
        if asset.status == FixedAssetStatus.SCRAPPED: raise errors.RequestError(msg='FIXED_ASSET_SCRAPPED')
        target = await db.scalar(select(CostCenter).where(CostCenter.id == obj.target_cost_center_id, CostCenter.status == 'ACTIVE', CostCenter.deleted == 0))
        if not target: raise errors.NotFoundError(msg='COST_CENTER_NOT_FOUND')
        previous = asset.cost_center_id; asset.cost_center_id = target.id
        db.add(FixedAssetTransaction(asset_id=asset.id, transaction_type=FixedAssetTransactionType.TRANSFER, transaction_date=obj.transfer_date, amount=Decimal('0'), from_cost_center_id=previous, to_cost_center_id=target.id, description=obj.remark or '固定资产调拨'))
        await db.flush(); return await FinanceService._fixed_asset_detail(db, asset.id)

    @staticmethod
    async def add_fixed_asset_maintenance(db: AsyncSession, asset_id: int, obj: FixedAssetMaintenanceCreate) -> FixedAssetMaintenanceDetail:
        asset = await FinanceService._fixed_asset(db, asset_id)
        if asset.status == FixedAssetStatus.SCRAPPED: raise errors.RequestError(msg='FIXED_ASSET_SCRAPPED')
        period = await FinanceService._period(db, asset.period_id)
        row = FixedAssetMaintenance(asset_id=asset.id, maintenance_date=obj.maintenance_date, amount=obj.amount, vendor_name=obj.vendor_name, description=obj.description)
        db.add(row); await db.flush()
        voucher = await FinanceService._fixed_asset_voucher(db, period, 'FIXED_ASSET_MAINTENANCE', row.id, row.amount, '6602', '维修费用', '2202', '应付账款', f'固定资产维修 {asset.asset_name}', row.maintenance_date)
        row.voucher_id = voucher.id
        db.add(FixedAssetTransaction(asset_id=asset.id, transaction_type=FixedAssetTransactionType.MAINTENANCE, transaction_date=row.maintenance_date, amount=row.amount, voucher_id=voucher.id, description=row.description or '固定资产维修'))
        await db.flush(); return FixedAssetMaintenanceDetail.model_validate(row)

    @staticmethod
    async def dispose_fixed_asset(db: AsyncSession, asset_id: int, obj: FixedAssetDisposeRequest) -> FixedAssetDetail:
        asset = await FinanceService._fixed_asset(db, asset_id)
        if asset.status == FixedAssetStatus.SCRAPPED: return await FinanceService._fixed_asset_detail(db, asset.id)
        period = await FinanceService._period(db, asset.period_id)
        amount = money(asset.net_value)
        asset.status = FixedAssetStatus.SCRAPPED; asset.disposed_at = timezone.now(); asset.net_value = Decimal('0')
        voucher = await FinanceService._fixed_asset_voucher(db, period, 'FIXED_ASSET_DISPOSAL', asset.id, amount, '6602', '资产处置损益', '1601', '固定资产原值', f'固定资产报废 {asset.asset_name}', obj.disposal_date)
        db.add(FixedAssetTransaction(asset_id=asset.id, transaction_type=FixedAssetTransactionType.DISPOSAL, transaction_date=obj.disposal_date, amount=amount, voucher_id=voucher.id, description=obj.reason or '固定资产报废'))
        await db.flush(); return await FinanceService._fixed_asset_detail(db, asset.id)

    @staticmethod
    async def run_fixed_asset_depreciation(db: AsyncSession, period_id: int) -> FixedAssetDepreciationSummary:
        period = await FinanceService._period(db, period_id)
        if period.status == FinancePeriodStatus.CLOSED: raise errors.RequestError(msg='FINANCE_PERIOD_CLOSED')
        assets = (await db.scalars(select(FixedAsset).where(FixedAsset.status == FixedAssetStatus.ACTIVE, FixedAsset.acquisition_date <= period.end_date, FixedAsset.deleted == 0))).all()
        rows: list[FixedAssetDepreciationDetail] = []; total = Decimal('0')
        for asset in assets:
            existing = await db.scalar(select(FixedAssetDepreciation).where(FixedAssetDepreciation.asset_id == asset.id, FixedAssetDepreciation.period_id == period.id, FixedAssetDepreciation.deleted == 0))
            if existing: rows.append(FixedAssetDepreciationDetail.model_validate(existing)); total += money(existing.depreciation_amount); continue
            remaining = money(asset.net_value - asset.residual_value)
            amount = money(min(remaining, asset.original_value - asset.residual_value) / Decimal(asset.useful_life_months)) if remaining > 0 else Decimal('0')
            if amount <= 0: continue
            asset.accumulated_depreciation = money(asset.accumulated_depreciation + amount); asset.net_value = money(max(asset.residual_value, asset.net_value - amount))
            dep = FixedAssetDepreciation(asset_id=asset.id, period_id=period.id, depreciation_amount=amount, accumulated_depreciation=asset.accumulated_depreciation, net_value=asset.net_value, posted_at=timezone.now())
            db.add(dep); await db.flush()
            voucher = await FinanceService._fixed_asset_voucher(db, period, 'FIXED_ASSET_DEPRECIATION', dep.id, amount, '6602', '折旧费用', '1602', '累计折旧', f'固定资产折旧 {asset.asset_name}', period.end_date)
            dep.voucher_id = voucher.id
            db.add(FixedAssetTransaction(asset_id=asset.id, transaction_type=FixedAssetTransactionType.DEPRECIATION, transaction_date=period.end_date, amount=amount, voucher_id=voucher.id, description='月度折旧计提'))
            await db.flush(); rows.append(FixedAssetDepreciationDetail.model_validate(dep)); total += amount
        return FixedAssetDepreciationSummary(period_id=period.id, asset_count=len(rows), total_depreciation=money(total), rows=rows)

    @staticmethod
    async def create_fixed_asset_count(db: AsyncSession, obj: FixedAssetCountCreate) -> FixedAssetCountDetail:
        period = await FinanceService._period(db, obj.period_id)
        if period.status == FinancePeriodStatus.CLOSED: raise errors.RequestError(msg='FINANCE_PERIOD_CLOSED')
        if obj.assigned_user_id:
            user = await db.scalar(select(User).where(User.id == obj.assigned_user_id, User.deleted == 0, User.status == 1))
            if not user:
                raise errors.NotFoundError(msg='FIXED_ASSET_COUNT_ASSIGNEE_NOT_FOUND')
        task = FixedAssetCountTask(task_no=f'FAC-{period.period_code.replace("-", "")}-{timezone.now():%H%M%S%f}', period_id=period.id, status=FixedAssetCountStatus.COUNTING, zone_code=obj.zone_code, assigned_user_id=obj.assigned_user_id, counted_at=timezone.now(), remark=obj.remark)
        db.add(task); await db.flush()
        for item in obj.lines:
            asset = await FinanceService._fixed_asset(db, item.asset_id)
            variance = item.variance_type
            if not item.counted: variance = FixedAssetCountVariance.MISSING
            elif item.observed_cost_center_id and item.observed_cost_center_id != asset.cost_center_id: variance = FixedAssetCountVariance.LOCATION_MISMATCH
            db.add(FixedAssetCountLine(task_id=task.id, asset_id=asset.id, barcode_snapshot=asset.barcode, serial_snapshot=asset.serial_number, counted=item.counted, observed_cost_center_id=item.observed_cost_center_id, variance_type=variance, remark=item.remark, evidence_photo=item.evidence_photo, evidence_note=item.evidence_note))
        await db.flush(); return await FinanceService.fixed_asset_count_detail(db, task.id)

    @staticmethod
    async def fixed_asset_count_detail(db: AsyncSession, task_id: int) -> FixedAssetCountDetail:
        task = await db.scalar(select(FixedAssetCountTask).where(FixedAssetCountTask.id == task_id, FixedAssetCountTask.deleted == 0))
        if not task: raise errors.NotFoundError(msg='FIXED_ASSET_COUNT_NOT_FOUND')
        lines = (await db.scalars(select(FixedAssetCountLine).where(FixedAssetCountLine.task_id == task.id, FixedAssetCountLine.deleted == 0).order_by(FixedAssetCountLine.id))).all()
        return FixedAssetCountDetail.model_validate({**{key: getattr(task, key) for key in ('id','task_no','period_id','status','zone_code','assigned_user_id','counted_at','posted_at','remark')}, 'lines': lines})

    @staticmethod
    async def lookup_fixed_asset(db: AsyncSession, code: str) -> FixedAssetDetail:
        """按条码或序列号查询资产，供 PDA/手机扫码后即时展示账面信息。"""
        normalized = code.strip()
        if not normalized:
            raise errors.RequestError(msg='FIXED_ASSET_SCAN_CODE_REQUIRED')
        asset = await db.scalar(select(FixedAsset).where(FixedAsset.deleted == 0, sa.or_(FixedAsset.barcode == normalized, FixedAsset.serial_number == normalized)))
        if not asset:
            raise errors.NotFoundError(msg='FIXED_ASSET_SCAN_NOT_FOUND')
        return await FinanceService._fixed_asset_detail(db, asset.id)

    @staticmethod
    async def scan_fixed_asset_count(db: AsyncSession, task_id: int, obj: FixedAssetCountScanRequest) -> FixedAssetCountScanResult:
        """将一次扫码结果幂等写入盘点任务，并即时计算位置/缺失差异。"""
        task = await db.scalar(select(FixedAssetCountTask).where(FixedAssetCountTask.id == task_id, FixedAssetCountTask.deleted == 0))
        if not task:
            raise errors.NotFoundError(msg='FIXED_ASSET_COUNT_NOT_FOUND')
        if task.status != FixedAssetCountStatus.COUNTING:
            raise errors.RequestError(msg='FIXED_ASSET_COUNT_NOT_COUNTING')
        normalized = obj.code.strip()
        if not normalized:
            raise errors.RequestError(msg='FIXED_ASSET_SCAN_CODE_REQUIRED')
        asset = await db.scalar(select(FixedAsset).where(FixedAsset.deleted == 0, sa.or_(FixedAsset.barcode == normalized, FixedAsset.serial_number == normalized)))
        if not asset:
            raise errors.NotFoundError(msg='FIXED_ASSET_SCAN_NOT_FOUND')
        line = await db.scalar(select(FixedAssetCountLine).where(FixedAssetCountLine.task_id == task.id, FixedAssetCountLine.asset_id == asset.id, FixedAssetCountLine.deleted == 0))
        is_new = line is None
        variance = obj.variance_type
        if not obj.counted:
            variance = FixedAssetCountVariance.MISSING
        elif obj.observed_cost_center_id and obj.observed_cost_center_id != asset.cost_center_id:
            variance = FixedAssetCountVariance.LOCATION_MISMATCH
        if line is None:
            line = FixedAssetCountLine(task_id=task.id, asset_id=asset.id, barcode_snapshot=asset.barcode, serial_snapshot=asset.serial_number, counted=obj.counted, observed_cost_center_id=obj.observed_cost_center_id, variance_type=variance, remark=obj.remark, evidence_photo=obj.evidence_photo, evidence_note=obj.evidence_note)
            db.add(line)
        else:
            line.barcode_snapshot = asset.barcode
            line.serial_snapshot = asset.serial_number
            line.counted = obj.counted
            line.observed_cost_center_id = obj.observed_cost_center_id
            line.variance_type = variance
            line.remark = obj.remark
            if obj.evidence_photo is not None:
                line.evidence_photo = obj.evidence_photo
            if obj.evidence_note is not None:
                line.evidence_note = obj.evidence_note
            line.approval_status = FixedAssetCountApprovalStatus.PENDING
            line.approved_by = None
            line.approved_at = None
        await db.flush()
        return FixedAssetCountScanResult(task_id=task.id, asset=await FinanceService._fixed_asset_detail(db, asset.id), line=FixedAssetCountLineDetail.model_validate(line), is_new=is_new)

    @staticmethod
    async def approve_fixed_asset_count_line(db: AsyncSession, task_id: int, line_id: int, obj: FixedAssetCountApprovalRequest) -> FixedAssetCountLineDetail:
        task = await db.scalar(select(FixedAssetCountTask).where(FixedAssetCountTask.id == task_id, FixedAssetCountTask.deleted == 0))
        if not task:
            raise errors.NotFoundError(msg='FIXED_ASSET_COUNT_NOT_FOUND')
        if task.status != FixedAssetCountStatus.COUNTING:
            raise errors.RequestError(msg='FIXED_ASSET_COUNT_NOT_COUNTING')
        line = await db.scalar(select(FixedAssetCountLine).where(FixedAssetCountLine.id == line_id, FixedAssetCountLine.task_id == task.id, FixedAssetCountLine.deleted == 0).with_for_update())
        if not line:
            raise errors.NotFoundError(msg='FIXED_ASSET_COUNT_LINE_NOT_FOUND')
        if line.variance_type == FixedAssetCountVariance.NONE:
            raise errors.RequestError(msg='FIXED_ASSET_COUNT_NO_VARIANCE_TO_APPROVE')
        if line.approval_status == FixedAssetCountApprovalStatus.APPROVED and obj.status == FixedAssetCountApprovalStatus.REJECTED:
            raise errors.RequestError(msg='FIXED_ASSET_COUNT_APPROVAL_FINALIZED')
        if obj.status == FixedAssetCountApprovalStatus.APPROVED and line.variance_type in (FixedAssetCountVariance.MISSING, FixedAssetCountVariance.DAMAGED) and not (obj.evidence_photo or line.evidence_photo):
            raise errors.RequestError(msg='FIXED_ASSET_COUNT_EVIDENCE_REQUIRED')
        if obj.evidence_photo is not None:
            line.evidence_photo = obj.evidence_photo
        if obj.evidence_note is not None:
            line.evidence_note = obj.evidence_note
        line.approval_status = obj.status
        line.approved_by = FinanceService._operator_id()
        line.approved_at = timezone.now()
        await db.flush()
        return FixedAssetCountLineDetail.model_validate(line)

    @staticmethod
    async def post_fixed_asset_count(db: AsyncSession, task_id: int) -> FixedAssetCountDetail:
        task = await db.scalar(select(FixedAssetCountTask).where(FixedAssetCountTask.id == task_id, FixedAssetCountTask.deleted == 0))
        if not task: raise errors.NotFoundError(msg='FIXED_ASSET_COUNT_NOT_FOUND')
        if task.status == FixedAssetCountStatus.POSTED: return await FinanceService.fixed_asset_count_detail(db, task.id)
        lines = (await db.scalars(select(FixedAssetCountLine).where(FixedAssetCountLine.task_id == task.id, FixedAssetCountLine.deleted == 0))).all()
        if any(line.variance_type != FixedAssetCountVariance.NONE and line.approval_status != FixedAssetCountApprovalStatus.APPROVED for line in lines):
            raise errors.RequestError(msg='FIXED_ASSET_COUNT_APPROVAL_REQUIRED')
        for line in lines:
            asset = await FinanceService._fixed_asset(db, line.asset_id)
            if line.variance_type in (FixedAssetCountVariance.MISSING, FixedAssetCountVariance.DAMAGED):
                asset.status = FixedAssetStatus.RETIRED; asset.disposed_at = timezone.now()
            elif line.variance_type == FixedAssetCountVariance.LOCATION_MISMATCH and line.observed_cost_center_id:
                previous = asset.cost_center_id; asset.cost_center_id = line.observed_cost_center_id
                db.add(FixedAssetTransaction(asset_id=asset.id, transaction_type=FixedAssetTransactionType.COUNT_ADJUSTMENT, transaction_date=timezone.now().date(), amount=Decimal('0'), from_cost_center_id=previous, to_cost_center_id=asset.cost_center_id, description='固定资产盘点位置差异调整'))
            if line.variance_type != FixedAssetCountVariance.NONE and line.variance_type != FixedAssetCountVariance.LOCATION_MISMATCH:
                db.add(FixedAssetTransaction(asset_id=asset.id, transaction_type=FixedAssetTransactionType.COUNT_ADJUSTMENT, transaction_date=timezone.now().date(), amount=asset.net_value, description=f'固定资产盘点差异：{line.variance_type}'))
        task.status = FixedAssetCountStatus.POSTED; task.posted_at = timezone.now(); await db.flush(); return await FinanceService.fixed_asset_count_detail(db, task.id)

    @staticmethod
    async def run_fixed_asset_dual_depreciation(db: AsyncSession, period_id: int) -> FixedAssetDualDepreciationSummary:
        book = await FinanceService.run_fixed_asset_depreciation(db, period_id)
        period = await FinanceService._period(db, period_id)
        assets = (await db.scalars(select(FixedAsset).where(FixedAsset.status == FixedAssetStatus.ACTIVE, FixedAsset.acquisition_date <= period.end_date, FixedAsset.deleted == 0))).all()
        rows: list[FixedAssetDualDepreciationDetail] = []; total_tax = Decimal('0'); total_book = Decimal('0')
        for asset in assets:
            book_row = next((row for row in book.rows if row.asset_id == asset.id), None)
            existing = await db.scalar(select(FixedAssetTaxDepreciation).where(FixedAssetTaxDepreciation.asset_id == asset.id, FixedAssetTaxDepreciation.period_id == period.id, FixedAssetTaxDepreciation.deleted == 0))
            if not existing:
                remaining = money(asset.original_value - asset.tax_accumulated_depreciation)
                amount = money(min(remaining, asset.original_value / Decimal(asset.useful_life_months))) if remaining > 0 else Decimal('0')
                asset.tax_accumulated_depreciation = money(asset.tax_accumulated_depreciation + amount); asset.tax_net_value = money(max(Decimal('0'), asset.original_value - asset.tax_accumulated_depreciation))
                existing = FixedAssetTaxDepreciation(asset_id=asset.id, period_id=period.id, depreciation_amount=amount, accumulated_depreciation=asset.tax_accumulated_depreciation, net_value=asset.tax_net_value, posted_at=timezone.now())
                db.add(existing); await db.flush()
            total_tax += money(existing.depreciation_amount); total_book += money(book_row.depreciation_amount if book_row else 0)
            rows.append(FixedAssetDualDepreciationDetail(asset_id=asset.id, book_depreciation_amount=money(book_row.depreciation_amount if book_row else 0), book_accumulated_depreciation=asset.accumulated_depreciation, book_net_value=asset.net_value, tax_depreciation_amount=existing.depreciation_amount, tax_accumulated_depreciation=asset.tax_accumulated_depreciation, tax_net_value=asset.tax_net_value, book_tax_difference=money((book_row.depreciation_amount if book_row else 0) - existing.depreciation_amount), book_voucher_id=book_row.voucher_id if book_row else None))
        await db.flush(); return FixedAssetDualDepreciationSummary(period_id=period_id, asset_count=len(rows), total_book_depreciation=money(total_book), total_tax_depreciation=money(total_tax), total_difference=money(total_book - total_tax), rows=rows)

    @staticmethod
    async def budget_alerts(db: AsyncSession, period_id: int | None = None) -> list[BudgetAlertDetail]:
        query = select(BudgetAlert).join(FinanceBudgetLine, FinanceBudgetLine.id == BudgetAlert.budget_line_id).join(FinanceBudget, FinanceBudget.id == FinanceBudgetLine.budget_id).where(BudgetAlert.deleted == 0, FinanceBudget.deleted == 0)
        if period_id: query = query.where(FinanceBudget.period_id == period_id)
        rows = (await db.scalars(query.order_by(BudgetAlert.triggered_at.desc()))).all()
        return [BudgetAlertDetail.model_validate(row) for row in rows]

    @staticmethod
    def _boundaries(period: FinancePeriod) -> tuple[datetime, datetime]:
        return datetime.combine(period.start_date, time.min, tzinfo=timezone.tz_info), datetime.combine(period.end_date + timedelta(days=1), time.min, tzinfo=timezone.tz_info)

    @staticmethod
    async def calculate_inventory_valuation(db: AsyncSession, period_id: int) -> list[InventoryValuationDetail]:
        period = await FinanceService._period(db, period_id)
        if period.status == FinancePeriodStatus.CLOSED:
            raise errors.RequestError(msg='FINANCE_PERIOD_CLOSED')
        start_at, end_at = FinanceService._boundaries(period)
        material_ids = list((await db.scalars(select(StockTransaction.material_id).where(StockTransaction.occurred_at < end_at).distinct())).all())
        receipt_rates: dict[int, Decimal] = {}
        for tx_id, price in (await db.execute(select(SupplierReceiptLine.stock_transaction_id, PurchaseOrderLine.unit_price).join(PurchaseOrderLine, PurchaseOrderLine.id == SupplierReceiptLine.purchase_order_line_id).where(SupplierReceiptLine.deleted == 0, PurchaseOrderLine.deleted == 0, SupplierReceiptLine.stock_transaction_id.is_not(None), PurchaseOrderLine.unit_price.is_not(None)))).all():
            receipt_rates[tx_id] = money(price)
        production_rates = {row.work_order_id: money(row.unit_cost) for row in (await db.scalars(select(WorkOrderCost).where(WorkOrderCost.deleted == 0, WorkOrderCost.status == 'POSTED'))).all()}
        positive_types = {StockTransactionType.RECEIPT.value, StockTransactionType.PRODUCTION_RECEIPT.value, StockTransactionType.RETURN.value, StockTransactionType.CUSTOMER_RETURN.value, StockTransactionType.TRANSFER_IN.value}
        negative_types = {StockTransactionType.ISSUE.value, StockTransactionType.SHIPMENT.value, StockTransactionType.SCRAP.value, StockTransactionType.PURCHASE_RETURN.value, StockTransactionType.TRANSFER_OUT.value}
        result: list[InventoryValuationDetail] = []
        for material_id in material_ids:
            material = await db.scalar(select(Material).where(Material.id == material_id, Material.deleted == 0))
            if not material:
                continue
            txs = list((await db.scalars(select(StockTransaction).where(StockTransaction.material_id == material_id, StockTransaction.occurred_at < end_at).order_by(StockTransaction.occurred_at, StockTransaction.id))).all())
            qty = Decimal('0'); value = Decimal('0'); opening_qty = Decimal('0'); opening_value = Decimal('0'); receipt_qty = Decimal('0'); receipt_value = Decimal('0'); issue_qty = Decimal('0'); issue_value = Decimal('0'); known_receipt_qty = Decimal('0'); all_receipt_qty = Decimal('0')
            for tx in txs:
                occurred = tx.occurred_at
                delta = money(tx.quantity_delta)
                tx_type = str(getattr(tx.transaction_type, 'value', tx.transaction_type))
                if tx_type in positive_types and delta > 0:
                    rate = receipt_rates.get(tx.id)
                    if rate is None and tx.reference_type == 'WORK_ORDER' and tx.reference_id:
                        rate = production_rates.get(tx.reference_id)
                    if rate is None:
                        rate = money(value / qty) if qty > 0 else Decimal('0')
                    amount = money(delta * rate); all_receipt_qty += delta
                    if receipt_qty or occurred >= start_at:
                        if occurred >= start_at:
                            receipt_qty += delta; receipt_value += amount
                    if rate > 0:
                        known_receipt_qty += delta
                    qty += delta; value += amount
                elif tx_type in negative_types and delta < 0:
                    out_qty = -delta; rate = money(value / qty) if qty > 0 else Decimal('0'); amount = money(out_qty * rate)
                    if occurred >= start_at:
                        issue_qty += out_qty; issue_value += amount
                    qty += delta; value -= amount
                if occurred < start_at:
                    opening_qty = qty; opening_value = value
            closing_qty = qty; closing_value = max(value, Decimal('0')); coverage = money(known_receipt_qty / all_receipt_qty * 100) if all_receipt_qty else Decimal('100')
            existing = await db.scalar(select(InventoryValuation).where(InventoryValuation.period_id == period_id, InventoryValuation.material_id == material_id, InventoryValuation.deleted == 0))
            if existing:
                existing.deleted = 1; existing.deleted_time = timezone.now()
            row = InventoryValuation(period_id=period_id, material_id=material_id, material_code_snapshot=material.material_code, material_name_snapshot=material.material_name, opening_quantity=money(opening_qty), opening_value=money(opening_value), receipt_quantity=money(receipt_qty), receipt_value=money(receipt_value), issue_quantity=money(issue_qty), issue_value=money(issue_value), closing_quantity=money(closing_qty), closing_value=money(closing_value), unit_cost=money(closing_value / closing_qty) if closing_qty > 0 else Decimal('0'), coverage_rate=coverage, calculated_at=timezone.now())
            db.add(row); await db.flush()
            result.append(InventoryValuationDetail.model_validate(row))
        return result

    @staticmethod
    async def create_ar_invoice(db: AsyncSession, obj: ARInvoiceCreate) -> ARInvoice:
        customer = await db.scalar(select(Customer).where(Customer.id == obj.customer_id, Customer.deleted == 0))
        if not customer:
            raise errors.NotFoundError(msg='CUSTOMER_NOT_FOUND')
        if await db.scalar(select(ARInvoice).where(ARInvoice.invoice_no == obj.invoice_no, ARInvoice.deleted == 0)):
            raise errors.RequestError(msg='AR_INVOICE_ALREADY_EXISTS')
        invoice = ARInvoice(**obj.model_dump(), customer_code_snapshot=customer.customer_code, customer_name_snapshot=customer.customer_name)
        db.add(invoice); await db.flush(); await FinanceService._ensure_plan(db, PaymentPlanDirection.AR, invoice); return invoice

    @staticmethod
    async def create_ap_invoice(db: AsyncSession, obj: APInvoiceCreate) -> APInvoice:
        supplier = await db.scalar(select(Supplier).where(Supplier.id == obj.supplier_id, Supplier.deleted == 0))
        if not supplier:
            raise errors.NotFoundError(msg='SUPPLIER_NOT_FOUND')
        if await db.scalar(select(APInvoice).where(APInvoice.invoice_no == obj.invoice_no, APInvoice.deleted == 0)):
            raise errors.RequestError(msg='AP_INVOICE_ALREADY_EXISTS')
        payload = obj.model_dump(); payload.pop('supplier_id')
        invoice = APInvoice(**payload, supplier_id=supplier.id, supplier_code_snapshot=supplier.supplier_code, supplier_name_snapshot=supplier.supplier_name)
        db.add(invoice); await db.flush(); await FinanceService._ensure_plan(db, PaymentPlanDirection.AP, invoice); return invoice

    @staticmethod
    async def _ensure_plan(db: AsyncSession, direction: PaymentPlanDirection, invoice: ARInvoice | APInvoice) -> PaymentPlan:
        existing = await db.scalar(select(PaymentPlan).where(PaymentPlan.direction == direction, PaymentPlan.document_id == invoice.id, PaymentPlan.deleted == 0))
        if existing:
            return existing
        is_ar = direction == PaymentPlanDirection.AR
        plan = PaymentPlan(plan_no=f'{direction.value}-{invoice.invoice_no}', direction=direction, document_id=invoice.id, partner_id=invoice.customer_id if is_ar else invoice.supplier_id, partner_name_snapshot=invoice.customer_name_snapshot if is_ar else invoice.supplier_name_snapshot, due_date=invoice.due_date, planned_amount=invoice.total_amount, ar_invoice_id=invoice.id if is_ar else None, ap_invoice_id=invoice.id if not is_ar else None)
        db.add(plan); await db.flush(); return plan

    @staticmethod
    async def auto_ar_invoice(db: AsyncSession, shipment_id: int, obj: AutoInvoiceRequest) -> ARInvoice:
        shipment = await db.scalar(select(Shipment).where(Shipment.id == shipment_id, Shipment.deleted == 0))
        if not shipment:
            raise errors.NotFoundError(msg='SHIPMENT_NOT_FOUND')
        existing = await db.scalar(select(ARInvoice).where(ARInvoice.source_type == 'SHIPMENT', ARInvoice.source_id == shipment.id, ARInvoice.deleted == 0))
        if existing:
            return existing
        lines = list((await db.execute(select(ShipmentLine, SalesOrderLine).join(SalesOrderLine, SalesOrderLine.id == ShipmentLine.sales_order_line_id).where(ShipmentLine.shipment_id == shipment.id, ShipmentLine.deleted == 0, SalesOrderLine.deleted == 0))).all())
        net = money(sum((money(line.quantity) * money(order_line.unit_price) for line, order_line in lines), Decimal('0')))
        tax = money(net * obj.tax_rate / Decimal('100')); no = obj.invoice_no or f'AR-SH-{shipment.shipment_no}'
        return await FinanceService.create_ar_invoice(db, ARInvoiceCreate(invoice_no=no, customer_id=shipment.customer_id, invoice_date=obj.invoice_date, due_date=obj.due_date, net_amount=net, tax_amount=tax, total_amount=money(net + tax), source_type='SHIPMENT', source_id=shipment.id, source_no=shipment.shipment_no))

    @staticmethod
    async def auto_ap_invoice(db: AsyncSession, receipt_id: int, obj: AutoInvoiceRequest) -> APInvoice:
        receipt = await db.scalar(select(SupplierReceipt).where(SupplierReceipt.id == receipt_id, SupplierReceipt.deleted == 0))
        if not receipt:
            raise errors.NotFoundError(msg='SUPPLIER_RECEIPT_NOT_FOUND')
        existing = await db.scalar(select(APInvoice).where(APInvoice.source_type == 'SUPPLIER_RECEIPT', APInvoice.source_id == receipt.id, APInvoice.deleted == 0))
        if existing:
            return existing
        lines = list((await db.execute(select(SupplierReceiptLine, PurchaseOrderLine).join(PurchaseOrderLine, PurchaseOrderLine.id == SupplierReceiptLine.purchase_order_line_id).where(SupplierReceiptLine.supplier_receipt_id == receipt.id, SupplierReceiptLine.deleted == 0, PurchaseOrderLine.deleted == 0))).all())
        net = money(sum((money(line.quantity) * money(order_line.unit_price) for line, order_line in lines if order_line.unit_price is not None), Decimal('0')))
        tax = money(net * obj.tax_rate / Decimal('100')); no = obj.invoice_no or f'AP-RC-{receipt.receipt_no}'
        return await FinanceService.create_ap_invoice(db, APInvoiceCreate(invoice_no=no, supplier_id=receipt.supplier_id, invoice_date=obj.invoice_date, due_date=obj.due_date, net_amount=net, tax_amount=tax, total_amount=money(net + tax), source_type='SUPPLIER_RECEIPT', source_id=receipt.id, source_no=receipt.receipt_no))

    @staticmethod
    async def payment_plans(db: AsyncSession) -> list[PaymentPlan]:
        return list((await db.scalars(select(PaymentPlan).where(PaymentPlan.deleted == 0).order_by(PaymentPlan.due_date))).all())

    @staticmethod
    async def match_three_way(db: AsyncSession, obj: ThreeWayMatchRequest) -> ThreeWayMatchDetail:
        po_line = await db.scalar(select(PurchaseOrderLine).where(PurchaseOrderLine.id == obj.purchase_order_line_id, PurchaseOrderLine.deleted == 0))
        receipt_line = await db.scalar(select(SupplierReceiptLine).where(SupplierReceiptLine.id == obj.supplier_receipt_line_id, SupplierReceiptLine.deleted == 0))
        invoice = await db.scalar(select(APInvoice).where(APInvoice.id == obj.ap_invoice_id, APInvoice.deleted == 0))
        if not po_line or not receipt_line or not invoice:
            raise errors.NotFoundError(msg='THREE_WAY_MATCH_SOURCE_NOT_FOUND')
        if receipt_line.purchase_order_line_id != po_line.id or invoice.supplier_id != (await db.scalar(select(SupplierReceipt.supplier_id).where(SupplierReceipt.id == receipt_line.supplier_receipt_id))):
            raise errors.RequestError(msg='THREE_WAY_MATCH_SOURCE_MISMATCH')
        quantity_variance = money(receipt_line.quantity - po_line.ordered_quantity); invoice_unit_price = money(invoice.net_amount / receipt_line.quantity) if receipt_line.quantity else Decimal('0'); price_variance = money(invoice_unit_price - money(po_line.unit_price))
        if abs(quantity_variance) > Decimal('0.000001'):
            status = ThreeWayMatchStatus.QUANTITY_VARIANCE
        elif abs(price_variance) > Decimal('0.000001'):
            status = ThreeWayMatchStatus.PRICE_VARIANCE
        else:
            status = ThreeWayMatchStatus.MATCHED
        existing = await db.scalar(select(ThreeWayMatch).where(ThreeWayMatch.purchase_order_line_id == po_line.id, ThreeWayMatch.supplier_receipt_line_id == receipt_line.id, ThreeWayMatch.ap_invoice_id == invoice.id, ThreeWayMatch.deleted == 0))
        if existing:
            row = existing
        else:
            row = ThreeWayMatch(purchase_order_line_id=po_line.id, supplier_receipt_line_id=receipt_line.id, ap_invoice_id=invoice.id, ordered_quantity=po_line.ordered_quantity, received_quantity=receipt_line.quantity, invoiced_quantity=receipt_line.quantity, ordered_unit_price=money(po_line.unit_price), invoiced_unit_price=invoice_unit_price)
            db.add(row)
        row.quantity_variance = quantity_variance; row.price_variance = price_variance; row.status = status; row.matched_at = timezone.now(); await db.flush(); return ThreeWayMatchDetail.model_validate(row)

    @staticmethod
    async def create_bank_statement(db: AsyncSession, obj: BankStatementCreate) -> BankStatement:
        if await db.scalar(select(BankStatement).where(BankStatement.statement_no == obj.statement_no, BankStatement.deleted == 0)):
            raise errors.RequestError(msg='BANK_STATEMENT_ALREADY_EXISTS')
        row = BankStatement(**obj.model_dump(), imported_at=timezone.now()); db.add(row); await db.flush(); return row

    @staticmethod
    async def bank_statements(db: AsyncSession) -> list[BankStatement]:
        return list((await db.scalars(select(BankStatement).where(BankStatement.deleted == 0).order_by(BankStatement.transaction_date.desc(), BankStatement.id.desc()))).all())

    @staticmethod
    async def reconcile_bank(db: AsyncSession, obj: BankReconcileRequest) -> BankStatement:
        statement = await db.scalar(select(BankStatement).where(BankStatement.id == obj.statement_id, BankStatement.deleted == 0))
        if not statement:
            raise errors.NotFoundError(msg='BANK_STATEMENT_NOT_FOUND')
        if obj.target_type == 'AR_RECEIPT':
            target = await db.scalar(select(ARReceipt).where(ARReceipt.id == obj.target_id, ARReceipt.deleted == 0)); expected_direction = BankDirection.IN
        else:
            target = await db.scalar(select(APPayment).where(APPayment.id == obj.target_id, APPayment.deleted == 0)); expected_direction = BankDirection.OUT
        if not target:
            raise errors.NotFoundError(msg='SETTLEMENT_NOT_FOUND')
        if statement.direction != expected_direction or obj.amount > money(target.amount):
            raise errors.RequestError(msg='BANK_RECONCILIATION_MISMATCH')
        if await db.scalar(select(BankReconciliation).where(BankReconciliation.statement_id == statement.id, BankReconciliation.target_type == obj.target_type, BankReconciliation.target_id == obj.target_id, BankReconciliation.deleted == 0)):
            raise errors.RequestError(msg='BANK_RECONCILIATION_ALREADY_EXISTS')
        matched = money(await db.scalar(select(func.coalesce(func.sum(BankReconciliation.matched_amount), 0)).where(BankReconciliation.statement_id == statement.id, BankReconciliation.deleted == 0)))
        if matched + obj.amount > money(statement.amount):
            raise errors.RequestError(msg='BANK_RECONCILIATION_EXCEEDS_STATEMENT')
        db.add(BankReconciliation(statement_id=statement.id, target_type=obj.target_type, target_id=obj.target_id, matched_amount=obj.amount, matched_at=timezone.now())); await db.flush()
        statement.status = BankStatementStatus.MATCHED if matched + obj.amount == money(statement.amount) else BankStatementStatus.PARTIAL; await db.flush(); return statement

    @staticmethod
    async def auto_reconcile_bank(db: AsyncSession, statement_id: int) -> BankStatement:
        statement = await db.scalar(select(BankStatement).where(BankStatement.id == statement_id, BankStatement.deleted == 0))
        if not statement:
            raise errors.NotFoundError(msg='BANK_STATEMENT_NOT_FOUND')
        if statement.direction == BankDirection.IN:
            target = await db.scalar(select(ARReceipt).where(ARReceipt.deleted == 0, ARReceipt.reference_no == statement.reference_no, ARReceipt.amount == statement.amount))
            target_type = 'AR_RECEIPT'
        else:
            target = await db.scalar(select(APPayment).where(APPayment.deleted == 0, APPayment.reference_no == statement.reference_no, APPayment.amount == statement.amount))
            target_type = 'AP_PAYMENT'
        if not target:
            return statement
        return await FinanceService.reconcile_bank(db, BankReconcileRequest(statement_id=statement.id, target_type=target_type, target_id=target.id, amount=statement.amount))

    @staticmethod
    async def settle_ar(db: AsyncSession, obj: SettlementCreate) -> ARReceipt:
        invoice = await db.scalar(select(ARInvoice).where(ARInvoice.id == obj.document_id, ARInvoice.deleted == 0))
        if not invoice:
            raise errors.NotFoundError(msg='AR_INVOICE_NOT_FOUND')
        remaining = money(invoice.total_amount - invoice.paid_amount)
        if obj.amount > remaining:
            raise errors.RequestError(msg='AR_RECEIPT_EXCEEDS_REMAINING')
        receipt = ARReceipt(receipt_no=f'AR-{timezone.now():%Y%m%d%H%M%S%f}', invoice_id=invoice.id, customer_id=invoice.customer_id, customer_name_snapshot=invoice.customer_name_snapshot, receipt_date=obj.settlement_date, amount=obj.amount, method=obj.method, reference_no=obj.reference_no, remark=obj.remark)
        invoice.paid_amount = money(invoice.paid_amount + obj.amount); invoice.status = 'PAID' if invoice.paid_amount >= invoice.total_amount else 'PARTIAL'
        db.add(receipt); await db.flush(); await FinanceService._update_plan(db, PaymentPlanDirection.AR, invoice.id, invoice.paid_amount, invoice.total_amount, invoice.due_date); return receipt

    @staticmethod
    async def settle_ap(db: AsyncSession, obj: SettlementCreate) -> APPayment:
        invoice = await db.scalar(select(APInvoice).where(APInvoice.id == obj.document_id, APInvoice.deleted == 0))
        if not invoice:
            raise errors.NotFoundError(msg='AP_INVOICE_NOT_FOUND')
        remaining = money(invoice.total_amount - invoice.paid_amount)
        if obj.amount > remaining:
            raise errors.RequestError(msg='AP_PAYMENT_EXCEEDS_REMAINING')
        payment = APPayment(payment_no=f'AP-{timezone.now():%Y%m%d%H%M%S%f}', invoice_id=invoice.id, supplier_id=invoice.supplier_id, supplier_name_snapshot=invoice.supplier_name_snapshot, payment_date=obj.settlement_date, amount=obj.amount, method=obj.method, reference_no=obj.reference_no, remark=obj.remark)
        invoice.paid_amount = money(invoice.paid_amount + obj.amount); invoice.status = 'PAID' if invoice.paid_amount >= invoice.total_amount else 'PARTIAL'
        db.add(payment); await db.flush(); await FinanceService._update_plan(db, PaymentPlanDirection.AP, invoice.id, invoice.paid_amount, invoice.total_amount, invoice.due_date); return payment

    @staticmethod
    async def _update_plan(db: AsyncSession, direction: PaymentPlanDirection, document_id: int, settled_amount: Decimal, planned_amount: Decimal, due_date: date) -> None:
        plan = await db.scalar(select(PaymentPlan).where(PaymentPlan.direction == direction, PaymentPlan.document_id == document_id, PaymentPlan.deleted == 0))
        if not plan:
            return
        plan.settled_amount = money(settled_amount)
        if settled_amount >= planned_amount:
            plan.status = PaymentPlanStatus.SETTLED
        elif due_date < timezone.now().date():
            plan.status = PaymentPlanStatus.OVERDUE
        else:
            plan.status = PaymentPlanStatus.PARTIAL

    @staticmethod
    async def generate_voucher(db: AsyncSession, obj: VoucherGenerateRequest) -> VoucherDetail:
        period = await FinanceService._period(db, obj.period_id)
        if period.status == FinancePeriodStatus.CLOSED:
            raise errors.RequestError(msg='FINANCE_PERIOD_CLOSED')
        source_type = obj.source_type.upper()
        existing = await db.scalar(select(GLVoucher).where(GLVoucher.source_type == source_type, GLVoucher.source_id == obj.source_id, GLVoucher.deleted == 0))
        if existing:
            return await FinanceService.voucher_detail(db, existing.id)
        debit_account = credit_account = ''; debit_name = credit_name = ''; amount = Decimal('0'); net_amount = Decimal('0'); tax_amount = Decimal('0'); customer_id = supplier_id = None; summary = source_type
        if source_type == VoucherSourceType.AR_INVOICE.value:
            source = await db.scalar(select(ARInvoice).where(ARInvoice.id == obj.source_id, ARInvoice.deleted == 0));
            if not source: raise errors.NotFoundError(msg='AR_INVOICE_NOT_FOUND')
            amount = money(source.total_amount); net_amount = money(source.net_amount); tax_amount = money(source.tax_amount); debit_account, debit_name, credit_account, credit_name = '1122', '应收账款', '6001', '主营业务收入'; customer_id = source.customer_id; summary = f'AR invoice {source.invoice_no}'
        elif source_type == VoucherSourceType.AP_INVOICE.value:
            source = await db.scalar(select(APInvoice).where(APInvoice.id == obj.source_id, APInvoice.deleted == 0));
            if not source: raise errors.NotFoundError(msg='AP_INVOICE_NOT_FOUND')
            amount = money(source.total_amount); net_amount = money(source.net_amount); tax_amount = money(source.tax_amount); debit_account, debit_name, credit_account, credit_name = '1401', '存货/费用', '2202', '应付账款'; supplier_id = source.supplier_id; summary = f'AP invoice {source.invoice_no}'
        elif source_type == VoucherSourceType.AR_RECEIPT.value:
            source = await db.scalar(select(ARReceipt).where(ARReceipt.id == obj.source_id, ARReceipt.deleted == 0));
            if not source: raise errors.NotFoundError(msg='AR_RECEIPT_NOT_FOUND')
            amount = money(source.amount); net_amount = amount; debit_account, debit_name, credit_account, credit_name = '1002', '银行存款', '1122', '应收账款'; customer_id = source.customer_id; summary = f'AR receipt {source.receipt_no}'
        elif source_type == VoucherSourceType.AP_PAYMENT.value:
            source = await db.scalar(select(APPayment).where(APPayment.id == obj.source_id, APPayment.deleted == 0));
            if not source: raise errors.NotFoundError(msg='AP_PAYMENT_NOT_FOUND')
            amount = money(source.amount); net_amount = amount; debit_account, debit_name, credit_account, credit_name = '2202', '应付账款', '1002', '银行存款'; supplier_id = source.supplier_id; summary = f'AP payment {source.payment_no}'
        else:
            raise errors.RequestError(msg='UNSUPPORTED_VOUCHER_SOURCE')
        voucher = GLVoucher(voucher_no=f'V-{period.period_code.replace("-", "")}-{timezone.now():%H%M%S%f}', period_id=period.id, voucher_date=period.end_date if period.end_date < timezone.now().date() else timezone.now().date(), source_type=source_type, source_id=obj.source_id, summary=summary, total_debit=amount, total_credit=amount, status=VoucherStatus.POSTED, posted_at=timezone.now())
        db.add(voucher); await db.flush()
        line_specs: list[tuple[str, str, Decimal, Decimal]] = [(debit_account, debit_name, amount, Decimal('0'))]
        if source_type == VoucherSourceType.AR_INVOICE.value:
            line_specs.append((credit_account, credit_name, Decimal('0'), net_amount))
            if tax_amount > 0:
                line_specs.append(('2221', '应交税费-销项税', Decimal('0'), tax_amount))
        elif source_type == VoucherSourceType.AP_INVOICE.value:
            line_specs = [(debit_account, debit_name, net_amount, Decimal('0'))]
            if tax_amount > 0:
                line_specs.append(('2221', '应交税费-进项税', tax_amount, Decimal('0')))
            line_specs.append((credit_account, credit_name, Decimal('0'), amount))
        else:
            line_specs.append((credit_account, credit_name, Decimal('0'), amount))
        db.add_all([GLVoucherLine(voucher_id=voucher.id, line_no=index, account_code=account, account_name=name, debit=debit, credit=credit, customer_id=customer_id, supplier_id=supplier_id, description=summary) for index, (account, name, debit, credit) in enumerate(line_specs, start=1)])
        await db.flush(); return await FinanceService.voucher_detail(db, voucher.id)

    @staticmethod
    async def voucher_detail(db: AsyncSession, voucher_id: int) -> VoucherDetail:
        voucher = await db.scalar(select(GLVoucher).where(GLVoucher.id == voucher_id, GLVoucher.deleted == 0))
        if not voucher: raise errors.NotFoundError(msg='VOUCHER_NOT_FOUND')
        lines = list((await db.scalars(select(GLVoucherLine).where(GLVoucherLine.voucher_id == voucher.id, GLVoucherLine.deleted == 0).order_by(GLVoucherLine.line_no))).all())
        return VoucherDetail.model_validate({**{key: getattr(voucher, key) for key in ('id', 'voucher_no', 'period_id', 'voucher_date', 'source_type', 'source_id', 'summary', 'total_debit', 'total_credit', 'status', 'posted_at')}, 'lines': lines})

    @staticmethod
    async def dashboard(db: AsyncSession, period_id: int | None = None) -> FinanceDashboard:
        period = await FinanceService._period(db, period_id) if period_id else None
        date_filters = []
        if period:
            date_filters = [ARInvoice.invoice_date >= period.start_date, ARInvoice.invoice_date <= period.end_date]
        valuation_query = select(func.coalesce(func.sum(InventoryValuation.closing_value), 0)).where(InventoryValuation.deleted == 0, *([InventoryValuation.period_id == period_id] if period else []))
        inventory_value = money(await db.scalar(valuation_query))
        ar_rows = list((await db.scalars(select(ARInvoice).where(ARInvoice.deleted == 0, *date_filters))).all())
        ap_filters = [APInvoice.invoice_date >= period.start_date, APInvoice.invoice_date <= period.end_date] if period else []
        ap_rows = list((await db.scalars(select(APInvoice).where(APInvoice.deleted == 0, *ap_filters))).all())
        today = timezone.now().date()
        ar = money(sum((money(row.total_amount - row.paid_amount) for row in ar_rows), Decimal('0'))); overdue_ar = money(sum((money(row.total_amount - row.paid_amount) for row in ar_rows if row.due_date < today and row.paid_amount < row.total_amount), Decimal('0')))
        ap = money(sum((money(row.total_amount - row.paid_amount) for row in ap_rows), Decimal('0'))); overdue_ap = money(sum((money(row.total_amount - row.paid_amount) for row in ap_rows if row.due_date < today and row.paid_amount < row.total_amount), Decimal('0')))
        voucher_query = select(GLVoucherLine.account_code, func.sum(GLVoucherLine.credit), func.sum(GLVoucherLine.debit)).join(GLVoucher, GLVoucher.id == GLVoucherLine.voucher_id).where(GLVoucher.deleted == 0, GLVoucherLine.deleted == 0, *([GLVoucher.period_id == period_id] if period else []))
        revenue = Decimal('0'); cogs = Decimal('0')
        for account, credit, debit in (await db.execute(voucher_query.group_by(GLVoucherLine.account_code))).all():
            if account == '6001': revenue += money(credit or 0)
            if account == '6401': cogs += money(debit or 0)
        costing_period = await db.scalar(select(CostPeriod).where(CostPeriod.period_code == period.period_code, CostPeriod.deleted == 0)) if period else None
        if costing_period:
            margin = await costing_service.margin(db, costing_period.id, MarginDimension.PRODUCT)
            if not revenue:
                revenue = money(margin.revenue)
            if not cogs:
                cogs = money(margin.cogs)
        ar_receipts = await db.scalar(select(func.coalesce(func.sum(ARReceipt.amount), 0)).where(ARReceipt.deleted == 0, *([ARReceipt.receipt_date >= period.start_date, ARReceipt.receipt_date <= period.end_date] if period else [])))
        ap_payments = await db.scalar(select(func.coalesce(func.sum(APPayment.amount), 0)).where(APPayment.deleted == 0, *([APPayment.payment_date >= period.start_date, APPayment.payment_date <= period.end_date] if period else [])))
        voucher_count = int(await db.scalar(select(func.count(GLVoucher.id)).where(GLVoucher.deleted == 0, *([GLVoucher.period_id == period_id] if period else []))) or 0)
        profit = money(revenue - cogs)
        return FinanceDashboard(period_id=period.id if period else None, period_code=period.period_code if period else None, inventory_value=inventory_value, accounts_receivable=ar, overdue_receivable=overdue_ar, accounts_payable=ap, overdue_payable=overdue_ap, revenue=money(revenue), cogs=money(cogs), gross_profit=profit, gross_margin_rate=money(profit / revenue * 100) if revenue else Decimal('0'), cash_in=money(ar_receipts), cash_out=money(ap_payments), voucher_count=voucher_count)


finance_service = FinanceService()
