from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.common.exception import errors
from backend.plugin.material.model import Material
from backend.plugin.quality.enums import (
    InspectionStatus,
    InspectionTemplateStatus,
    InspectionType,
    InspectionValueType,
    QualityConfigStatus,
)
from backend.plugin.quality.model import (
    QualityInspection,
    QualityInspectionItem,
    QualityInspectionResultLine,
    QualityInspectionStandard,
    QualityInspectionTemplate,
    QualitySamplingPlan,
)
from backend.plugin.quality.schema.quality_standard import (
    CreateQualityInspectionItem,
    CreateQualityInspectionStandard,
    CreateQualityInspectionTemplate,
    CreateQualitySamplingPlan,
    SubmitQualityResults,
)


class QualityStandardService:
    @staticmethod
    async def list_items(db: AsyncSession):
        return (await db.scalars(
            select(QualityInspectionItem)
            .where(QualityInspectionItem.deleted == 0)
            .order_by(QualityInspectionItem.item_code)
        )).all()

    @staticmethod
    async def create_item(db: AsyncSession, obj: CreateQualityInspectionItem):
        if await db.scalar(select(QualityInspectionItem.id).where(QualityInspectionItem.item_code == obj.item_code, QualityInspectionItem.deleted == 0)):
            raise errors.ConflictError(msg='QUALITY_INSPECTION_ITEM_EXISTS')
        row = QualityInspectionItem(**obj.model_dump())
        db.add(row)
        await db.flush()
        return row

    @staticmethod
    async def set_item_status(db: AsyncSession, item_id: int, status: QualityConfigStatus):
        row = await db.scalar(select(QualityInspectionItem).where(QualityInspectionItem.id == item_id, QualityInspectionItem.deleted == 0).with_for_update())
        if not row:
            raise errors.NotFoundError(msg='QUALITY_INSPECTION_ITEM_NOT_FOUND')
        row.status = status
        await db.flush()
        return row

    @staticmethod
    async def list_sampling_plans(db: AsyncSession):
        return (await db.scalars(
            select(QualitySamplingPlan)
            .where(QualitySamplingPlan.deleted == 0)
            .order_by(QualitySamplingPlan.plan_code)
        )).all()

    @staticmethod
    async def create_sampling_plan(db: AsyncSession, obj: CreateQualitySamplingPlan):
        if await db.scalar(select(QualitySamplingPlan.id).where(QualitySamplingPlan.plan_code == obj.plan_code, QualitySamplingPlan.deleted == 0)):
            raise errors.ConflictError(msg='QUALITY_SAMPLING_PLAN_EXISTS')
        row = QualitySamplingPlan(**obj.model_dump())
        db.add(row)
        await db.flush()
        return row

    @staticmethod
    async def set_sampling_plan_status(db: AsyncSession, plan_id: int, status: QualityConfigStatus):
        row = await db.scalar(select(QualitySamplingPlan).where(QualitySamplingPlan.id == plan_id, QualitySamplingPlan.deleted == 0).with_for_update())
        if not row:
            raise errors.NotFoundError(msg='QUALITY_SAMPLING_PLAN_NOT_FOUND')
        row.status = status
        await db.flush()
        return row

    @staticmethod
    async def list_templates(db: AsyncSession):
        return (await db.scalars(
            select(QualityInspectionTemplate)
            .where(QualityInspectionTemplate.deleted == 0)
            .order_by(QualityInspectionTemplate.created_time.desc())
        )).all()

    @staticmethod
    async def template(db: AsyncSession, template_id: int, *, lock: bool = False):
        stmt = select(QualityInspectionTemplate).where(QualityInspectionTemplate.id == template_id, QualityInspectionTemplate.deleted == 0)
        if lock:
            stmt = stmt.with_for_update()
        row = await db.scalar(stmt)
        if not row:
            raise errors.NotFoundError(msg='QUALITY_INSPECTION_TEMPLATE_NOT_FOUND')
        return row

    @staticmethod
    async def create_template(db: AsyncSession, obj: CreateQualityInspectionTemplate):
        if not await db.scalar(select(Material.id).where(Material.id == obj.material_id, Material.deleted == 0)):
            raise errors.NotFoundError(msg='MATERIAL_NOT_FOUND')
        if obj.inspection_type == InspectionType.INCOMING and obj.sampling_plan_id is None:
            raise errors.RequestError(msg='INCOMING_TEMPLATE_SAMPLING_REQUIRED')
        if obj.sampling_plan_id:
            plan = await db.scalar(select(QualitySamplingPlan).where(QualitySamplingPlan.id == obj.sampling_plan_id, QualitySamplingPlan.deleted == 0))
            if not plan or plan.status != QualityConfigStatus.ACTIVE:
                raise errors.ConflictError(msg='QUALITY_SAMPLING_PLAN_NOT_ACTIVE')
        duplicate = await db.scalar(select(QualityInspectionTemplate.id).where(
            QualityInspectionTemplate.material_id == obj.material_id,
            QualityInspectionTemplate.inspection_type == obj.inspection_type,
            QualityInspectionTemplate.template_version == obj.template_version,
            QualityInspectionTemplate.deleted == 0,
        ))
        if duplicate:
            raise errors.ConflictError(msg='QUALITY_INSPECTION_TEMPLATE_EXISTS')
        row = QualityInspectionTemplate(**obj.model_dump())
        db.add(row)
        await db.flush()
        return row

    @staticmethod
    async def standards(db: AsyncSession, template_id: int):
        await QualityStandardService.template(db, template_id)
        return (await db.scalars(
            select(QualityInspectionStandard)
            .where(QualityInspectionStandard.template_id == template_id, QualityInspectionStandard.deleted == 0)
            .order_by(QualityInspectionStandard.line_no)
        )).all()

    @staticmethod
    async def add_standard(db: AsyncSession, template_id: int, obj: CreateQualityInspectionStandard):
        template = await QualityStandardService.template(db, template_id, lock=True)
        if template.status != InspectionTemplateStatus.DRAFT:
            raise errors.ConflictError(msg='QUALITY_TEMPLATE_NOT_DRAFT')
        item = await db.scalar(select(QualityInspectionItem).where(QualityInspectionItem.id == obj.inspection_item_id, QualityInspectionItem.deleted == 0))
        if not item or item.status != QualityConfigStatus.ACTIVE:
            raise errors.ConflictError(msg='QUALITY_INSPECTION_ITEM_NOT_ACTIVE')
        duplicate = await db.scalar(select(QualityInspectionStandard.id).where(
            QualityInspectionStandard.template_id == template_id,
            ((QualityInspectionStandard.line_no == obj.line_no) | (QualityInspectionStandard.inspection_item_id == obj.inspection_item_id)),
            QualityInspectionStandard.deleted == 0,
        ))
        if duplicate:
            raise errors.ConflictError(msg='QUALITY_INSPECTION_STANDARD_EXISTS')
        if item.value_type == InspectionValueType.BOOLEAN and obj.expected_boolean is None:
            raise errors.RequestError(msg='EXPECTED_BOOLEAN_REQUIRED')
        row = QualityInspectionStandard(template_id=template.id, **obj.model_dump())
        db.add(row)
        await db.flush()
        return row

    @staticmethod
    async def set_template_status(db: AsyncSession, template_id: int, status: InspectionTemplateStatus):
        template = await QualityStandardService.template(db, template_id, lock=True)
        if status == InspectionTemplateStatus.ACTIVE:
            standards = await QualityStandardService.standards(db, template.id)
            if not standards:
                raise errors.ConflictError(msg='QUALITY_TEMPLATE_HAS_NO_STANDARDS')
            if template.sampling_plan_id:
                sampling = await db.scalar(select(QualitySamplingPlan).where(QualitySamplingPlan.id == template.sampling_plan_id, QualitySamplingPlan.deleted == 0))
                if not sampling or sampling.status != QualityConfigStatus.ACTIVE:
                    raise errors.ConflictError(msg='QUALITY_SAMPLING_PLAN_NOT_ACTIVE')
        template.status = status
        await db.flush()
        return template

    @staticmethod
    async def results(db: AsyncSession, inspection_id: int):
        return (await db.scalars(
            select(QualityInspectionResultLine)
            .where(QualityInspectionResultLine.inspection_id == inspection_id, QualityInspectionResultLine.deleted == 0)
            .order_by(QualityInspectionResultLine.line_no_snapshot)
        )).all()

    @staticmethod
    async def submit_results(db: AsyncSession, inspection_id: int, obj: SubmitQualityResults):
        inspection = await db.scalar(select(QualityInspection).where(QualityInspection.id == inspection_id, QualityInspection.deleted == 0).with_for_update())
        if not inspection:
            raise errors.NotFoundError(msg='QUALITY_INSPECTION_NOT_FOUND')
        if inspection.status != InspectionStatus.PENDING:
            raise errors.ConflictError(msg='QUALITY_INSPECTION_NOT_PENDING')
        template = await QualityStandardService.template(db, obj.template_id)
        if template.status != InspectionTemplateStatus.ACTIVE or template.material_id != inspection.material_id or template.inspection_type != inspection.inspection_type:
            raise errors.ConflictError(msg='QUALITY_TEMPLATE_NOT_APPLICABLE')
        standards = {item.id: item for item in await QualityStandardService.standards(db, template.id)}
        submitted_ids = {item.standard_id for item in obj.results}
        required_ids = {item.id for item in standards.values() if item.required}
        if not required_ids.issubset(submitted_ids):
            raise errors.RequestError(msg='REQUIRED_QUALITY_RESULTS_MISSING')
        if await db.scalar(select(QualityInspectionResultLine.id).where(QualityInspectionResultLine.inspection_id == inspection.id, QualityInspectionResultLine.deleted == 0)):
            raise errors.ConflictError(msg='QUALITY_RESULTS_ALREADY_SUBMITTED')
        result_rows = []
        for submitted in obj.results:
            standard = standards.get(submitted.standard_id)
            if not standard:
                raise errors.NotFoundError(msg='QUALITY_INSPECTION_STANDARD_NOT_FOUND')
            item = await db.scalar(select(QualityInspectionItem).where(QualityInspectionItem.id == standard.inspection_item_id, QualityInspectionItem.deleted == 0))
            if not item:
                raise errors.NotFoundError(msg='QUALITY_INSPECTION_ITEM_NOT_FOUND')
            if item.value_type == InspectionValueType.NUMERIC:
                if submitted.numeric_value is None:
                    raise errors.RequestError(msg='NUMERIC_QUALITY_VALUE_REQUIRED')
                qualified = (standard.lower_limit is None or submitted.numeric_value >= standard.lower_limit) and (standard.upper_limit is None or submitted.numeric_value <= standard.upper_limit)
            elif item.value_type == InspectionValueType.BOOLEAN:
                if submitted.boolean_value is None:
                    raise errors.RequestError(msg='BOOLEAN_QUALITY_VALUE_REQUIRED')
                qualified = submitted.boolean_value == standard.expected_boolean
            else:
                if not submitted.text_value:
                    raise errors.RequestError(msg='TEXT_QUALITY_VALUE_REQUIRED')
                qualified = standard.expected_text is None or submitted.text_value == standard.expected_text
            row = QualityInspectionResultLine(
                inspection_id=inspection.id,
                template_id=template.id,
                standard_id=standard.id,
                inspection_item_id=item.id,
                line_no_snapshot=standard.line_no,
                item_code_snapshot=item.item_code,
                item_name_snapshot=item.item_name,
                value_type_snapshot=item.value_type,
                is_qualified=qualified,
                lower_limit_snapshot=standard.lower_limit,
                upper_limit_snapshot=standard.upper_limit,
                expected_boolean_snapshot=standard.expected_boolean,
                expected_text_snapshot=standard.expected_text,
                numeric_value=submitted.numeric_value,
                boolean_value=submitted.boolean_value,
                text_value=submitted.text_value,
                remark=submitted.remark,
            )
            db.add(row)
            result_rows.append(row)
        await db.flush()
        return result_rows


quality_standard_service = QualityStandardService()
