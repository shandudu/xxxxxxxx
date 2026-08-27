"""Validate budget approval, expense reimbursement and threshold alerts."""
from __future__ import annotations
import argparse
import asyncio
from datetime import date
from decimal import Decimal
from backend.common.exception import errors
from backend.database.db import async_db_session
from backend.plugin.demo.service.demo_service import demo_service
from backend.plugin.finance.schema.finance import BudgetCreate, CostCenterCreate, ExpenseClaimCreate, ExpenseLineCreate, FinancePeriodCreate
from backend.plugin.finance.service import finance_service

class _Rollback(Exception): pass

async def validate(commit: bool) -> None:
    async with async_db_session() as db:
        try:
            async with db.begin():
                await demo_service.run_sales_order_driven(db)
                period = await finance_service.create_period(db, FinancePeriodCreate(period_code='2099-11-BUDGET', start_date=date(2099,11,1), end_date=date(2099,11,30)))
                center = await finance_service.create_cost_center(db, CostCenterCreate(center_code='CC-DEMO', center_name='演示成本中心'))
                budget = await finance_service.create_budget(db, BudgetCreate(period_id=period.id, budget_name='部门运营预算', cost_center_id=center.id, lines=[{'account_code':'6602','category':'差旅费','budget_amount':Decimal('100'),'warning_threshold':Decimal('80')}]))
                budget = await finance_service.approve_budget(db, budget.id)
                line_id = budget.lines[0].id
                claim = await finance_service.create_expense_claim(db, ExpenseClaimCreate(period_id=period.id, applicant_id=1, expense_date=date(2099,11,5), cost_center_id=center.id, description='差旅报销', lines=[ExpenseLineCreate(category='差旅费', amount=Decimal('80'), budget_line_id=line_id)]))
                claim = await finance_service.approve_expense_claim(db, claim.id)
                overrun_blocked = False
                second = await finance_service.create_expense_claim(db, ExpenseClaimCreate(period_id=period.id, applicant_id=1, expense_date=date(2099,11,6), cost_center_id=center.id, lines=[ExpenseLineCreate(category='差旅费', amount=Decimal('30'), budget_line_id=line_id)]))
                try:
                    await finance_service.approve_expense_claim(db, second.id)
                except Exception:
                    overrun_blocked = True
                alerts = await finance_service.budget_alerts(db, period.id)
                if claim.status != 'APPROVED' or not overrun_blocked or not alerts:
                    raise RuntimeError('budget/expense validation failed')
                print(f'BUDGET_EXPENSE_OK budget={budget.total_amount} claim={claim.total_amount} alerts={len(alerts)} voucher={claim.voucher_id}')
                if not commit: raise _Rollback
        except _Rollback:
            print('BUDGET_EXPENSE_ROLLBACK_OK')

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--commit', action='store_true'); asyncio.run(validate(parser.parse_args().commit))
if __name__ == '__main__': main()
