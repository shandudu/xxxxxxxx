from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy import select

from backend.common.response.response_schema import ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db import CurrentSession, CurrentSessionTransaction
from backend.plugin.finance.schema.finance import APInvoiceCreate, ARInvoiceCreate, AutoInvoiceRequest, BankReconcileRequest, BankStatementCreate, BankStatementDetail, BudgetAlertDetail, BudgetCreate, BudgetDetail, CashFlowForecastSummary, ClosingCheckDetail, CostCenterCreate, CostCenterDetail, ExpenseClaimCreate, ExpenseClaimDetail, FinancePeriodCreate, FinancePeriodDetail, FinanceDashboard, FixedAssetCountApprovalRequest, FixedAssetCountCreate, FixedAssetCountDetail, FixedAssetCountScanRequest, FixedAssetCountScanResult, FixedAssetCreate, FixedAssetDetail, FixedAssetDepreciationSummary, FixedAssetDisposeRequest, FixedAssetDualDepreciationSummary, FixedAssetFromReceiptRequest, FixedAssetMaintenanceCreate, FixedAssetMaintenanceDetail, FixedAssetTransferRequest, InventoryCountCreate, InventoryCountDetail, InventoryValuationDetail, PaymentPlanDetail, SettlementCreate, TaxInvoiceDetail, TaxInvoiceSyncRequest, ThreeWayMatchDetail, ThreeWayMatchRequest, VoucherDetail, VoucherGenerateRequest
from backend.plugin.finance.model import TaxInvoiceLedger
from backend.plugin.finance.service import finance_service

router = APIRouter()
view_dependencies = [DependsJwtAuth, Depends(RequestPermission('erp:finance:view')), DependsRBAC]


@router.get('/periods', dependencies=view_dependencies)
async def periods(db: CurrentSession) -> ResponseSchemaModel[list[FinancePeriodDetail]]:
    return response_base.success(data=await finance_service.periods(db))


@router.post('/periods', dependencies=[Depends(RequestPermission('erp:finance:manage')), DependsRBAC])
async def create_period(db: CurrentSessionTransaction, obj: FinancePeriodCreate) -> ResponseSchemaModel[FinancePeriodDetail]:
    return response_base.success(data=await finance_service.create_period(db, obj))


@router.post('/periods/{period_id}/closing/check', dependencies=[Depends(RequestPermission('erp:finance:close')), DependsRBAC])
async def closing_check(db: CurrentSessionTransaction, period_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[list[ClosingCheckDetail]]:
    return response_base.success(data=await finance_service.closing_checks(db, period_id))


@router.post('/periods/{period_id}/closing/close', dependencies=[Depends(RequestPermission('erp:finance:close')), DependsRBAC])
async def close_period(db: CurrentSessionTransaction, period_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[FinancePeriodDetail]:
    return response_base.success(data=await finance_service.close_period(db, period_id))


@router.post('/cost-centers', dependencies=[Depends(RequestPermission('erp:finance:budget')), DependsRBAC])
async def create_cost_center(db: CurrentSessionTransaction, obj: CostCenterCreate) -> ResponseSchemaModel[CostCenterDetail]:
    return response_base.success(data=await finance_service.create_cost_center(db, obj))


@router.get('/cost-centers', dependencies=view_dependencies)
async def cost_centers(db: CurrentSession) -> ResponseSchemaModel[list[CostCenterDetail]]:
    return response_base.success(data=await finance_service.cost_centers(db))


@router.post('/budgets', dependencies=[Depends(RequestPermission('erp:finance:budget')), DependsRBAC])
async def create_budget(db: CurrentSessionTransaction, obj: BudgetCreate) -> ResponseSchemaModel[BudgetDetail]:
    return response_base.success(data=await finance_service.create_budget(db, obj))


@router.get('/budgets', dependencies=view_dependencies)
async def budgets(db: CurrentSession, period_id: int | None = Query(default=None, ge=1)) -> ResponseSchemaModel[list[BudgetDetail]]:
    return response_base.success(data=await finance_service.budgets(db, period_id))


@router.post('/budgets/{budget_id}/approve', dependencies=[Depends(RequestPermission('erp:finance:budget')), DependsRBAC])
async def approve_budget(db: CurrentSessionTransaction, budget_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[BudgetDetail]:
    return response_base.success(data=await finance_service.approve_budget(db, budget_id))


@router.get('/budget-alerts', dependencies=view_dependencies)
async def budget_alerts(db: CurrentSession, period_id: int | None = Query(default=None, ge=1)) -> ResponseSchemaModel[list[BudgetAlertDetail]]:
    return response_base.success(data=await finance_service.budget_alerts(db, period_id))


@router.post('/expenses', dependencies=[Depends(RequestPermission('erp:finance:expense')), DependsRBAC])
async def create_expense(db: CurrentSessionTransaction, obj: ExpenseClaimCreate) -> ResponseSchemaModel[ExpenseClaimDetail]:
    return response_base.success(data=await finance_service.create_expense_claim(db, obj))


@router.get('/expenses/{claim_id}', dependencies=view_dependencies)
async def expense(db: CurrentSession, claim_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[ExpenseClaimDetail]:
    return response_base.success(data=await finance_service.expense_claim_detail(db, claim_id))


@router.post('/expenses/{claim_id}/approve', dependencies=[Depends(RequestPermission('erp:finance:expense')), DependsRBAC])
async def approve_expense(db: CurrentSessionTransaction, claim_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[ExpenseClaimDetail]:
    return response_base.success(data=await finance_service.approve_expense_claim(db, claim_id))


@router.post('/expenses/{claim_id}/reject', dependencies=[Depends(RequestPermission('erp:finance:expense')), DependsRBAC])
async def reject_expense(db: CurrentSessionTransaction, claim_id: Annotated[int, Path(ge=1)], reason: str | None = Query(default=None, max_length=500)) -> ResponseSchemaModel[ExpenseClaimDetail]:
    return response_base.success(data=await finance_service.reject_expense_claim(db, claim_id, reason))


@router.post('/expenses/{claim_id}/pay', dependencies=[Depends(RequestPermission('erp:finance:expense')), DependsRBAC])
async def pay_expense(db: CurrentSessionTransaction, claim_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[ExpenseClaimDetail]:
    return response_base.success(data=await finance_service.mark_expense_paid(db, claim_id))


@router.post('/fixed-assets', dependencies=[Depends(RequestPermission('erp:finance:asset')), DependsRBAC])
async def create_fixed_asset(db: CurrentSessionTransaction, obj: FixedAssetCreate) -> ResponseSchemaModel[FixedAssetDetail]:
    return response_base.success(data=await finance_service.create_fixed_asset(db, obj))


@router.post('/fixed-assets/from-receipts/{receipt_id}', dependencies=[Depends(RequestPermission('erp:finance:asset')), DependsRBAC])
async def create_fixed_asset_from_receipt(db: CurrentSessionTransaction, receipt_id: Annotated[int, Path(ge=1)], obj: FixedAssetFromReceiptRequest) -> ResponseSchemaModel[FixedAssetDetail]:
    return response_base.success(data=await finance_service.create_fixed_asset_from_receipt(db, receipt_id, obj))


@router.get('/fixed-assets', dependencies=view_dependencies)
async def fixed_assets(db: CurrentSession, status: str | None = Query(default=None, max_length=20)) -> ResponseSchemaModel[list[FixedAssetDetail]]:
    return response_base.success(data=await finance_service.fixed_assets(db, status))


@router.get('/fixed-assets/lookup', dependencies=view_dependencies)
async def lookup_fixed_asset(db: CurrentSession, code: Annotated[str, Query(min_length=1, max_length=120)]) -> ResponseSchemaModel[FixedAssetDetail]:
    return response_base.success(data=await finance_service.lookup_fixed_asset(db, code))


@router.get('/fixed-assets/{asset_id}', dependencies=view_dependencies)
async def fixed_asset(db: CurrentSession, asset_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[FixedAssetDetail]:
    return response_base.success(data=await finance_service._fixed_asset_detail(db, asset_id))


@router.post('/fixed-assets/{asset_id}/transfer', dependencies=[Depends(RequestPermission('erp:finance:asset')), DependsRBAC])
async def transfer_fixed_asset(db: CurrentSessionTransaction, asset_id: Annotated[int, Path(ge=1)], obj: FixedAssetTransferRequest) -> ResponseSchemaModel[FixedAssetDetail]:
    return response_base.success(data=await finance_service.transfer_fixed_asset(db, asset_id, obj))


@router.post('/fixed-assets/{asset_id}/maintenance', dependencies=[Depends(RequestPermission('erp:finance:asset')), DependsRBAC])
async def fixed_asset_maintenance(db: CurrentSessionTransaction, asset_id: Annotated[int, Path(ge=1)], obj: FixedAssetMaintenanceCreate) -> ResponseSchemaModel[FixedAssetMaintenanceDetail]:
    return response_base.success(data=await finance_service.add_fixed_asset_maintenance(db, asset_id, obj))


@router.post('/fixed-assets/{asset_id}/dispose', dependencies=[Depends(RequestPermission('erp:finance:asset')), DependsRBAC])
async def dispose_fixed_asset(db: CurrentSessionTransaction, asset_id: Annotated[int, Path(ge=1)], obj: FixedAssetDisposeRequest) -> ResponseSchemaModel[FixedAssetDetail]:
    return response_base.success(data=await finance_service.dispose_fixed_asset(db, asset_id, obj))


@router.post('/fixed-assets/depreciation/run', dependencies=[Depends(RequestPermission('erp:finance:asset')), DependsRBAC])
async def run_fixed_asset_depreciation(db: CurrentSessionTransaction, period_id: Annotated[int, Query(ge=1)]) -> ResponseSchemaModel[FixedAssetDepreciationSummary]:
    return response_base.success(data=await finance_service.run_fixed_asset_depreciation(db, period_id))


@router.post('/fixed-assets/depreciation/dual-run', dependencies=[Depends(RequestPermission('erp:finance:asset')), DependsRBAC])
async def run_fixed_asset_dual_depreciation(db: CurrentSessionTransaction, period_id: Annotated[int, Query(ge=1)]) -> ResponseSchemaModel[FixedAssetDualDepreciationSummary]:
    return response_base.success(data=await finance_service.run_fixed_asset_dual_depreciation(db, period_id))


@router.post('/fixed-assets/counts', dependencies=[Depends(RequestPermission('erp:finance:asset')), DependsRBAC])
async def create_fixed_asset_count(db: CurrentSessionTransaction, obj: FixedAssetCountCreate) -> ResponseSchemaModel[FixedAssetCountDetail]:
    return response_base.success(data=await finance_service.create_fixed_asset_count(db, obj))


@router.get('/fixed-assets/counts/{task_id}', dependencies=view_dependencies)
async def fixed_asset_count(db: CurrentSession, task_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[FixedAssetCountDetail]:
    return response_base.success(data=await finance_service.fixed_asset_count_detail(db, task_id))


@router.post('/fixed-assets/counts/{task_id}/scan', dependencies=[Depends(RequestPermission('erp:finance:asset')), DependsRBAC])
async def scan_fixed_asset_count(db: CurrentSessionTransaction, task_id: Annotated[int, Path(ge=1)], obj: FixedAssetCountScanRequest) -> ResponseSchemaModel[FixedAssetCountScanResult]:
    return response_base.success(data=await finance_service.scan_fixed_asset_count(db, task_id, obj))


@router.post('/fixed-assets/counts/{task_id}/lines/{line_id}/approval', dependencies=[Depends(RequestPermission('erp:finance:asset')), DependsRBAC])
async def approve_fixed_asset_count_line(db: CurrentSessionTransaction, task_id: Annotated[int, Path(ge=1)], line_id: Annotated[int, Path(ge=1)], obj: FixedAssetCountApprovalRequest) -> ResponseSchemaModel:
    return response_base.success(data=await finance_service.approve_fixed_asset_count_line(db, task_id, line_id, obj))


@router.post('/fixed-assets/counts/{task_id}/post', dependencies=[Depends(RequestPermission('erp:finance:asset')), DependsRBAC])
async def post_fixed_asset_count(db: CurrentSessionTransaction, task_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[FixedAssetCountDetail]:
    return response_base.success(data=await finance_service.post_fixed_asset_count(db, task_id))


@router.post('/inventory/valuation/calculate', dependencies=[Depends(RequestPermission('erp:finance:valuate')), DependsRBAC])
async def calculate_inventory_valuation(db: CurrentSessionTransaction, period_id: Annotated[int, Query(ge=1)]) -> ResponseSchemaModel[list[InventoryValuationDetail]]:
    return response_base.success(data=await finance_service.calculate_inventory_valuation(db, period_id))


@router.post('/inventory/counts', dependencies=[Depends(RequestPermission('erp:finance:count')), DependsRBAC])
async def create_inventory_count(db: CurrentSessionTransaction, obj: InventoryCountCreate) -> ResponseSchemaModel[InventoryCountDetail]:
    return response_base.success(data=await finance_service.create_inventory_count(db, obj))


@router.get('/inventory/counts/{task_id}', dependencies=view_dependencies)
async def inventory_count(db: CurrentSession, task_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[InventoryCountDetail]:
    return response_base.success(data=await finance_service.inventory_count_detail(db, task_id))


@router.post('/inventory/counts/{task_id}/post', dependencies=[Depends(RequestPermission('erp:finance:count')), DependsRBAC])
async def post_inventory_count(db: CurrentSessionTransaction, task_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[InventoryCountDetail]:
    return response_base.success(data=await finance_service.post_inventory_count(db, task_id))


@router.post('/ar/invoices', dependencies=[Depends(RequestPermission('erp:finance:ar')), DependsRBAC])
async def create_ar_invoice(db: CurrentSessionTransaction, obj: ARInvoiceCreate):
    return response_base.success(data=await finance_service.create_ar_invoice(db, obj))


@router.post('/ar/invoices/from-shipments/{shipment_id}', dependencies=[Depends(RequestPermission('erp:finance:ar')), DependsRBAC])
async def auto_ar_invoice(db: CurrentSessionTransaction, shipment_id: Annotated[int, Path(ge=1)], obj: AutoInvoiceRequest):
    return response_base.success(data=await finance_service.auto_ar_invoice(db, shipment_id, obj))


@router.post('/ar/receipts', dependencies=[Depends(RequestPermission('erp:finance:ar')), DependsRBAC])
async def settle_ar(db: CurrentSessionTransaction, obj: SettlementCreate):
    return response_base.success(data=await finance_service.settle_ar(db, obj))


@router.post('/ap/invoices', dependencies=[Depends(RequestPermission('erp:finance:ap')), DependsRBAC])
async def create_ap_invoice(db: CurrentSessionTransaction, obj: APInvoiceCreate):
    return response_base.success(data=await finance_service.create_ap_invoice(db, obj))


@router.post('/ap/invoices/from-receipts/{receipt_id}', dependencies=[Depends(RequestPermission('erp:finance:ap')), DependsRBAC])
async def auto_ap_invoice(db: CurrentSessionTransaction, receipt_id: Annotated[int, Path(ge=1)], obj: AutoInvoiceRequest):
    return response_base.success(data=await finance_service.auto_ap_invoice(db, receipt_id, obj))


@router.get('/payment-plans', dependencies=view_dependencies)
async def payment_plans(db: CurrentSession) -> ResponseSchemaModel[list[PaymentPlanDetail]]:
    return response_base.success(data=await finance_service.payment_plans(db))


@router.post('/purchase/three-way-match', dependencies=[Depends(RequestPermission('erp:finance:ap')), DependsRBAC])
async def three_way_match(db: CurrentSessionTransaction, obj: ThreeWayMatchRequest) -> ResponseSchemaModel[ThreeWayMatchDetail]:
    return response_base.success(data=await finance_service.match_three_way(db, obj))


@router.post('/bank/statements', dependencies=[Depends(RequestPermission('erp:finance:bank')), DependsRBAC])
async def create_bank_statement(db: CurrentSessionTransaction, obj: BankStatementCreate) -> ResponseSchemaModel[BankStatementDetail]:
    return response_base.success(data=await finance_service.create_bank_statement(db, obj))


@router.get('/bank/statements', dependencies=view_dependencies)
async def bank_statements(db: CurrentSession) -> ResponseSchemaModel[list[BankStatementDetail]]:
    return response_base.success(data=await finance_service.bank_statements(db))


@router.post('/bank/reconcile', dependencies=[Depends(RequestPermission('erp:finance:bank')), DependsRBAC])
async def reconcile_bank(db: CurrentSessionTransaction, obj: BankReconcileRequest) -> ResponseSchemaModel[BankStatementDetail]:
    return response_base.success(data=await finance_service.reconcile_bank(db, obj))


@router.post('/bank/statements/{statement_id}/auto-reconcile', dependencies=[Depends(RequestPermission('erp:finance:bank')), DependsRBAC])
async def auto_reconcile_bank(db: CurrentSessionTransaction, statement_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[BankStatementDetail]:
    return response_base.success(data=await finance_service.auto_reconcile_bank(db, statement_id))


@router.post('/tax/invoices/sync', dependencies=[Depends(RequestPermission('erp:finance:tax')), DependsRBAC])
async def sync_tax_invoices(db: CurrentSessionTransaction, obj: TaxInvoiceSyncRequest) -> ResponseSchemaModel[list[TaxInvoiceDetail]]:
    return response_base.success(data=await finance_service.sync_tax_invoices(db, obj))


@router.get('/tax/invoices', dependencies=view_dependencies)
async def tax_invoices(db: CurrentSession, period_id: int | None = Query(default=None, ge=1)) -> ResponseSchemaModel[list[TaxInvoiceDetail]]:
    rows = list((await db.scalars(select(TaxInvoiceLedger).where(TaxInvoiceLedger.deleted == 0).order_by(TaxInvoiceLedger.issue_date.desc()))).all())
    return response_base.success(data=rows)


@router.post('/cash-flow/forecast/rebuild', dependencies=[Depends(RequestPermission('erp:finance:cashflow')), DependsRBAC])
async def rebuild_cash_flow(db: CurrentSessionTransaction, period_id: Annotated[int, Query(ge=1)]) -> ResponseSchemaModel[CashFlowForecastSummary]:
    return response_base.success(data=await finance_service.cash_flow_forecast(db, period_id, rebuild=True))


@router.get('/cash-flow/forecast', dependencies=view_dependencies)
async def cash_flow(db: CurrentSession, period_id: Annotated[int, Query(ge=1)]) -> ResponseSchemaModel[CashFlowForecastSummary]:
    return response_base.success(data=await finance_service.cash_flow_forecast(db, period_id))


@router.post('/ap/payments', dependencies=[Depends(RequestPermission('erp:finance:ap')), DependsRBAC])
async def settle_ap(db: CurrentSessionTransaction, obj: SettlementCreate):
    return response_base.success(data=await finance_service.settle_ap(db, obj))


@router.post('/vouchers/generate', dependencies=[Depends(RequestPermission('erp:finance:voucher')), DependsRBAC])
async def generate_voucher(db: CurrentSessionTransaction, obj: VoucherGenerateRequest) -> ResponseSchemaModel[VoucherDetail]:
    return response_base.success(data=await finance_service.generate_voucher(db, obj))


@router.get('/vouchers/{voucher_id}', dependencies=view_dependencies)
async def voucher(db: CurrentSession, voucher_id: Annotated[int, Path(ge=1)]) -> ResponseSchemaModel[VoucherDetail]:
    return response_base.success(data=await finance_service.voucher_detail(db, voucher_id))


@router.get('/dashboard', dependencies=view_dependencies)
async def dashboard(db: CurrentSession, period_id: int | None = Query(default=None, ge=1)) -> ResponseSchemaModel[FinanceDashboard]:
    return response_base.success(data=await finance_service.dashboard(db, period_id))
