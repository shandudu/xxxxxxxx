"""Seed configurable bilingual UI messages for phase two."""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'r8m1h3i5j7k9'
down_revision: str | None = 'q7l0g2h4i6j8'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


DICT_TYPES = (
    ('ui_tips', '界面提示词', '业务页面成功、警告、确认和帮助提示'),
    ('api_errors', '接口错误提示', '后端稳定错误 Key 的中英文提示'),
)

MESSAGES = (
    ('api_errors', 'request_failed', '请求失败', 'Request failed'),
    ('api_errors', 'validation_failed', '提交的数据校验失败', 'The submitted data is invalid'),
    ('api_errors', 'permission_denied', '没有执行该操作的权限', 'You do not have permission to perform this action'),
    ('api_errors', 'resource_not_found', '请求的业务数据不存在', 'The requested business record was not found'),
    ('api_errors', 'conflict', '业务数据已发生冲突，请刷新后重试', 'The business record has changed. Refresh and try again'),
    ('ui_tips', 'maintenance.requiredFields', '请填写所有必填项', 'Complete all required fields'),
    ('ui_tips', 'maintenance.planSaved', '运维计划已保存', 'Maintenance plan saved'),
    ('ui_tips', 'maintenance.tasksGenerated', '已生成 {count} 条运维任务', 'Generated {count} maintenance tasks'),
    ('ui_tips', 'maintenance.taskCompleted', '运维任务已完成', 'Maintenance task completed'),
    ('ui_tips', 'maintenance.repairCreated', '维修工单已创建', 'Repair order created'),
    ('ui_tips', 'maintenance.repairAssigned', '维修人员已指派', 'Repair technician assigned'),
    ('ui_tips', 'maintenance.repairCompleted', '维修已完成，关联停机已关闭', 'Repair completed and related downtime closed'),
    ('ui_tips', 'maintenance.partIssued', '备件已领用并扣减库存', 'Spare part issued and inventory deducted'),
    ('ui_tips', 'maintenance.costPosted', '维修费用已入账并生成总账凭证', 'Repair cost posted and general-ledger voucher generated'),
    ('ui_tips', 'maintenance.downtimeCreated', '停机记录已创建', 'Downtime record created'),
    ('ui_tips', 'maintenance.downtimeClosed', '停机记录已关闭', 'Downtime record closed'),
    ('ui_tips', 'maintenance.taskStartedWithDowntime', '任务已开始，计划停机已自动创建', 'Task started and planned downtime created automatically'),
    ('ui_tips', 'maintenance.taskStarted', '任务已开始', 'Task started'),
    ('ui_tips', 'maintenance.repairStarted', '维修已开始', 'Repair started'),
    ('ui_tips', 'maintenance.repairCancelled', '维修工单已取消', 'Repair order cancelled'),
    ('ui_tips', 'inventory.replenishment.generated', '已生成 {count} 条补货建议', 'Generated {count} replenishment suggestions'),
    ('ui_tips', 'inventory.replenishment.firmed', '补货建议已固定', 'Replenishment suggestion firmed'),
    ('ui_tips', 'inventory.replenishment.noSupplier', '没有可用供应商', 'No supplier is available'),
    ('ui_tips', 'inventory.replenishment.released', '补货建议已转正式业务单据', 'Replenishment suggestion released to a business document'),
    ('ui_tips', 'inventory.shelf_life.materialRequired', '请输入物料 ID', 'Enter a material ID'),
    ('ui_tips', 'inventory.shelf_life.policySaved', '效期与 FEFO 策略已保存', 'Shelf-life and FEFO policy saved'),
    ('ui_tips', 'inventory.shelf_life.risksRefreshed', '已刷新 {count} 个风险批次，过期批次已按策略冻结', 'Refreshed {count} at-risk lots; expired lots were frozen by policy'),
    ('ui_tips', 'inventory.shelf_life.alertAcknowledged', '预警已确认', 'Alert acknowledged'),
    ('ui_tips', 'inventory.shelf_life.reinspectionCreated', '复检单已创建，请在质量检验模块录入结果', 'Reinspection created; record the result in Quality Inspection'),
    ('ui_tips', 'inventory.shelf_life.releaseFieldsRequired', '请填写新效期和放行依据', 'Enter the new expiry date and release justification'),
    ('ui_tips', 'inventory.shelf_life.lotReleased', '批次已复检放行并更新效期', 'Lot released after reinspection and expiry date updated'),
    ('ui_tips', 'inventory.shelf_life.lotScrapped', '批次库存已报废', 'Lot inventory scrapped'),
    ('ui_tips', 'inventory.shelf_life.allocationFieldsRequired', '请输入物料、仓库和需求数量', 'Enter material, warehouse, and required quantity'),
    ('ui_tips', 'inventory.shelf_life.recallFieldsRequired', '请输入根批次和召回原因', 'Enter the root lot and recall reason'),
    ('ui_tips', 'inventory.shelf_life.recallCreated', '召回单已创建，相关库存已隔离，受影响发货已展开', 'Recall created, related inventory quarantined, and affected shipments identified'),
    ('ui_tips', 'inventory.shelf_life.impactClosed', '影响项已关闭', 'Impact item closed'),
    ('ui_tips', 'inventory.shelf_life.recallClosed', '召回闭环已完成', 'Recall closed'),
    ('ui_tips', 'supplier.lifecycle.applicationFieldsRequired', '请选择供应商并填写准入范围和资质文件引用', 'Select a supplier and enter the approval scope and qualification reference'),
    ('ui_tips', 'supplier.lifecycle.applicationCreated', '准入申请已创建，供应商采购资格暂时冻结', 'Approval application created; supplier purchasing eligibility is temporarily frozen'),
    ('ui_tips', 'supplier.lifecycle.applicationSubmitted', '准入申请已提交', 'Approval application submitted'),
    ('ui_tips', 'supplier.lifecycle.applicationApproved', '准入已批准，物料级 AVL 已生成', 'Approval granted and material-level AVL entries generated'),
    ('ui_tips', 'supplier.lifecycle.applicationRejected', '准入申请已拒绝', 'Approval application rejected'),
    ('ui_tips', 'supplier.lifecycle.applicationRequired', '请选择准入申请', 'Select an approval application'),
    ('ui_tips', 'supplier.lifecycle.auditCreated', '审厂任务已创建', 'Supplier audit task created'),
    ('ui_tips', 'supplier.lifecycle.auditRecorded', '审厂结论已记录', 'Supplier audit conclusion recorded'),
    ('ui_tips', 'supplier.lifecycle.sampleFieldsRequired', '请选择准入申请和物料', 'Select an approval application and material'),
    ('ui_tips', 'supplier.lifecycle.sampleCreated', '送样轮次已创建', 'Sample submission round created'),
    ('ui_tips', 'supplier.lifecycle.sampleRecorded', '样品结论已记录', 'Sample conclusion recorded'),
    ('ui_tips', 'supplier.lifecycle.ppapFieldsRequired', '请完整选择申请、物料、已批准样品并填写 PPAP 文件引用', 'Select the application, material, approved sample, and enter the PPAP file reference'),
    ('ui_tips', 'supplier.lifecycle.ppapCreated', 'PPAP 文件包已创建', 'PPAP package created'),
    ('ui_tips', 'supplier.lifecycle.ppapSubmitted', 'PPAP 已提交审批', 'PPAP submitted for approval'),
    ('ui_tips', 'supplier.lifecycle.ppapRecorded', 'PPAP 审批结论已记录', 'PPAP approval decision recorded'),
    ('ui_tips', 'supplier.lifecycle.reviewCreated', '定期复审任务已创建', 'Periodic review task created'),
    ('ui_tips', 'supplier.lifecycle.reviewsGenerated', '已生成 {count} 个到期复审任务', 'Generated {count} due review tasks'),
    ('ui_tips', 'supplier.lifecycle.reviewCompleted', '复审结论已联动 AVL 和采购资格', 'Review decision applied to AVL and purchasing eligibility'),
    ('ui_tips', 'quality.sqm.scarIssued', 'SCAR 已发布，整改时限默认为 14 天', 'SCAR issued with a default 14-day corrective-action deadline'),
    ('ui_tips', 'quality.sqm.responseFieldsRequired', '请完整填写遏制、根因、纠正和预防措施', 'Complete containment, root cause, corrective action, and preventive action'),
    ('ui_tips', 'quality.sqm.responseSubmitted', '供应商整改回复已提交', 'Supplier corrective-action response submitted'),
    ('ui_tips', 'quality.sqm.reinspectionCreated', '复验单已创建：{id}，请在质量检验页完成后再验证', 'Reinspection {id} created; complete it in Quality Inspection before verification'),
    ('ui_tips', 'quality.sqm.scarVerified', 'SCAR 验证完成，供应商评分已自动重算', 'SCAR verified and supplier score recalculated'),
    ('ui_tips', 'quality.sqm.supplierRequired', '请选择供应商', 'Select a supplier'),
    ('ui_tips', 'quality.sqm.scoreCompleted', '评分完成：{grade} 级 / {decision}', 'Scoring completed: Grade {grade} / {decision}'),
    ('ui_tips', 'quality.sqm.scoresRebuilt', '已重算 {count} 家供应商', 'Recalculated {count} suppliers'),
    ('ui_tips', 'quality.sqm.policySaved', '供应商评分与采购策略已保存', 'Supplier score and purchasing policy saved'),
    ('ui_tips', 'equipment.mold.fieldsRequired', '请完整填写模具、工装设备和产品', 'Complete the mold, tooling equipment, and product fields'),
    ('ui_tips', 'equipment.mold.created', '模具台账及穴位已创建', 'Mold record and cavities created'),
    ('ui_tips', 'equipment.mold.mountFieldsRequired', '请选择模具和生产设备', 'Select a mold and production equipment'),
    ('ui_tips', 'equipment.mold.mounted', '上模完成', 'Mold mounted'),
    ('ui_tips', 'equipment.mold.unmounted', '下模完成', 'Mold unmounted'),
    ('ui_tips', 'equipment.mold.taskCreated', '任务已创建', 'Task created'),
    ('ui_tips', 'equipment.mold.taskStarted', '任务已开始', 'Task started'),
    ('ui_tips', 'equipment.mold.maintenanceCompleted', '完工并归集成本', 'Maintenance completed and costs collected'),
    ('ui_tips', 'equipment.mold.cavityUpdated', '穴位状态已更新', 'Cavity status updated'),
)


def upgrade() -> None:
    bind = op.get_bind()
    insert_type = sa.text(
        'INSERT INTO sys_dict_type (name, code, remark, created_time, updated_time, deleted) '
        'SELECT :name, :code, :remark, CURRENT_TIMESTAMP, NULL, 0 '
        'WHERE NOT EXISTS (SELECT 1 FROM sys_dict_type WHERE code = :code AND deleted = 0)'
    )
    for code, name, remark in DICT_TYPES:
        bind.execute(insert_type, {'code': code, 'name': name, 'remark': remark})

    type_ids = dict(bind.execute(sa.text(
        "SELECT code, id FROM sys_dict_type WHERE code IN ('ui_tips', 'api_errors') AND deleted = 0"
    )).all())
    insert_message = sa.text(
        'INSERT INTO sys_dict_data '
        '(type_code, label, value, label_zh_cn, label_en_us, color, sort, status, remark, type_id, created_time, updated_time, deleted) '
        'SELECT :type_code, :zh, :value, :zh, :en, NULL, :sort, 1, :remark, :type_id, CURRENT_TIMESTAMP, NULL, 0 '
        'WHERE NOT EXISTS (SELECT 1 FROM sys_dict_data WHERE type_code = :type_code AND value = :value AND deleted = 0)'
    )
    for sort, (type_code, value, zh, en) in enumerate(MESSAGES, start=1):
        bind.execute(insert_message, {
            'type_code': type_code,
            'value': value,
            'zh': zh,
            'en': en,
            'sort': sort,
            'remark': f'内置可配置消息：{value}',
            'type_id': type_ids[type_code],
        })


def downgrade() -> None:
    bind = op.get_bind()
    delete_message = sa.text(
        'DELETE FROM sys_dict_data WHERE type_code = :type_code AND value = :value '
        'AND remark = :remark AND deleted = 0'
    )
    for type_code, value, _zh, _en in MESSAGES:
        bind.execute(delete_message, {
            'type_code': type_code,
            'value': value,
            'remark': f'内置可配置消息：{value}',
        })
    for code, _name, remark in DICT_TYPES:
        bind.execute(sa.text(
            'DELETE FROM sys_dict_type WHERE code = :code AND remark = :remark AND deleted = 0 '
            'AND NOT EXISTS (SELECT 1 FROM sys_dict_data WHERE type_code = :code AND deleted = 0)'
        ), {'code': code, 'remark': remark})
