from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from backend.common.pagination import DependsPagination, PageData
from backend.common.response.response_schema import ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db import CurrentSession, CurrentSessionTransaction
from backend.plugin.supplier.enums import (
    CooperationStatus,
    SupplierAvlStatus,
    SupplierQualificationStatus,
    SupplierQualityStatus,
    SupplierReviewStatus,
    SupplierStatus,
)
from backend.plugin.supplier.schema.lifecycle import (
    ApprovedMaterialDetail,
    CompletePeriodicReview,
    CompleteQualificationAudit,
    CreatePeriodicReview,
    CreatePpapSubmission,
    CreateQualificationApplication,
    CreateQualificationAudit,
    CreateSampleApproval,
    DecidePpapSubmission,
    DecideSampleApproval,
    PeriodicReviewDetail,
    PpapSubmissionDetail,
    QualificationApplicationDetail,
    QualificationAuditDetail,
    QualificationDecision,
    RejectQualification,
    SampleApprovalDetail,
    SupplierLifecycleDashboard,
)
from backend.plugin.supplier.schema.supplier import (
    CreateSupplierCategoryParam,
    CreateSupplierContactParam,
    CreateSupplierMaterialParam,
    CreateSupplierParam,
    SupplierCategoryDetail,
    SupplierCategoryStatusParam,
    SupplierCategoryTreeNode,
    SupplierContactDetail,
    SupplierContactStatusParam,
    SupplierCooperationParam,
    SupplierDetail,
    SupplierListItem,
    SupplierMaterialDetail,
    SupplierMaterialStatusParam,
    SupplierOption,
    SupplierQualityParam,
    SupplierStatusParam,
    UpdateSupplierCategoryParam,
    UpdateSupplierContactParam,
    UpdateSupplierMaterialParam,
    UpdateSupplierParam,
)
from backend.plugin.supplier.service import supplier_lifecycle_service, supplier_service


router = APIRouter()
view_dependencies = [DependsJwtAuth, Depends(RequestPermission('erp:supplier:view')), DependsRBAC]
lifecycle_view_dependencies = [
    DependsJwtAuth, Depends(RequestPermission('erp:supplier:lifecycle:view')), DependsRBAC,
]


@router.get('/lifecycle/dashboard', dependencies=lifecycle_view_dependencies)
async def supplier_lifecycle_dashboard(db: CurrentSession) -> ResponseSchemaModel[SupplierLifecycleDashboard]:
    return response_base.success(data=await supplier_lifecycle_service.dashboard(db))


@router.get('/lifecycle/applications', dependencies=lifecycle_view_dependencies)
async def list_qualification_applications(
    db: CurrentSession,
    supplier_id: Annotated[int | None, Query(ge=1)] = None,
    status: Annotated[SupplierQualificationStatus | None, Query()] = None,
) -> ResponseSchemaModel[list[QualificationApplicationDetail]]:
    return response_base.success(data=await supplier_lifecycle_service.list_applications(db, supplier_id, status))


@router.post(
    '/lifecycle/applications',
    dependencies=[Depends(RequestPermission('erp:supplier:lifecycle:qualification')), DependsRBAC],
)
async def create_qualification_application(
    db: CurrentSessionTransaction, obj: CreateQualificationApplication
) -> ResponseSchemaModel[QualificationApplicationDetail]:
    return response_base.success(data=await supplier_lifecycle_service.create_application(db, obj))


@router.post(
    '/lifecycle/applications/{application_id}/submit',
    dependencies=[Depends(RequestPermission('erp:supplier:lifecycle:qualification')), DependsRBAC],
)
async def submit_qualification_application(
    db: CurrentSessionTransaction, application_id: Annotated[int, Path(ge=1)]
) -> ResponseSchemaModel[QualificationApplicationDetail]:
    return response_base.success(data=await supplier_lifecycle_service.submit_application(db, application_id))


@router.post(
    '/lifecycle/applications/{application_id}/approve',
    dependencies=[Depends(RequestPermission('erp:supplier:lifecycle:approve')), DependsRBAC],
)
async def approve_qualification_application(
    db: CurrentSessionTransaction,
    application_id: Annotated[int, Path(ge=1)],
    obj: QualificationDecision,
) -> ResponseSchemaModel[QualificationApplicationDetail]:
    return response_base.success(data=await supplier_lifecycle_service.approve_application(db, application_id, obj))


@router.post(
    '/lifecycle/applications/{application_id}/reject',
    dependencies=[Depends(RequestPermission('erp:supplier:lifecycle:approve')), DependsRBAC],
)
async def reject_qualification_application(
    db: CurrentSessionTransaction,
    application_id: Annotated[int, Path(ge=1)],
    obj: RejectQualification,
) -> ResponseSchemaModel[QualificationApplicationDetail]:
    return response_base.success(data=await supplier_lifecycle_service.reject_application(db, application_id, obj))


@router.get('/lifecycle/audits', dependencies=lifecycle_view_dependencies)
async def list_qualification_audits(
    db: CurrentSession, application_id: Annotated[int | None, Query(ge=1)] = None
) -> ResponseSchemaModel[list[QualificationAuditDetail]]:
    return response_base.success(data=await supplier_lifecycle_service.list_audits(db, application_id))


@router.post(
    '/lifecycle/applications/{application_id}/audits',
    dependencies=[Depends(RequestPermission('erp:supplier:lifecycle:audit')), DependsRBAC],
)
async def create_qualification_audit(
    db: CurrentSessionTransaction,
    application_id: Annotated[int, Path(ge=1)],
    obj: CreateQualificationAudit,
) -> ResponseSchemaModel[QualificationAuditDetail]:
    return response_base.success(data=await supplier_lifecycle_service.create_audit(db, application_id, obj))


@router.post(
    '/lifecycle/audits/{audit_id}/complete',
    dependencies=[Depends(RequestPermission('erp:supplier:lifecycle:audit')), DependsRBAC],
)
async def complete_qualification_audit(
    db: CurrentSessionTransaction,
    audit_id: Annotated[int, Path(ge=1)],
    obj: CompleteQualificationAudit,
) -> ResponseSchemaModel[QualificationAuditDetail]:
    return response_base.success(data=await supplier_lifecycle_service.complete_audit(db, audit_id, obj))


@router.get('/lifecycle/samples', dependencies=lifecycle_view_dependencies)
async def list_sample_approvals(
    db: CurrentSession, application_id: Annotated[int | None, Query(ge=1)] = None
) -> ResponseSchemaModel[list[SampleApprovalDetail]]:
    return response_base.success(data=await supplier_lifecycle_service.list_samples(db, application_id))


@router.post(
    '/lifecycle/applications/{application_id}/samples',
    dependencies=[Depends(RequestPermission('erp:supplier:lifecycle:sample')), DependsRBAC],
)
async def create_sample_approval(
    db: CurrentSessionTransaction,
    application_id: Annotated[int, Path(ge=1)],
    obj: CreateSampleApproval,
) -> ResponseSchemaModel[SampleApprovalDetail]:
    return response_base.success(data=await supplier_lifecycle_service.create_sample(db, application_id, obj))


@router.post(
    '/lifecycle/samples/{sample_id}/decision',
    dependencies=[Depends(RequestPermission('erp:supplier:lifecycle:sample')), DependsRBAC],
)
async def decide_sample_approval(
    db: CurrentSessionTransaction,
    sample_id: Annotated[int, Path(ge=1)],
    obj: DecideSampleApproval,
) -> ResponseSchemaModel[SampleApprovalDetail]:
    return response_base.success(data=await supplier_lifecycle_service.decide_sample(db, sample_id, obj))


@router.get('/lifecycle/ppaps', dependencies=lifecycle_view_dependencies)
async def list_ppap_submissions(
    db: CurrentSession, application_id: Annotated[int | None, Query(ge=1)] = None
) -> ResponseSchemaModel[list[PpapSubmissionDetail]]:
    return response_base.success(data=await supplier_lifecycle_service.list_ppaps(db, application_id))


@router.post(
    '/lifecycle/applications/{application_id}/ppaps',
    dependencies=[Depends(RequestPermission('erp:supplier:lifecycle:ppap')), DependsRBAC],
)
async def create_ppap_submission(
    db: CurrentSessionTransaction,
    application_id: Annotated[int, Path(ge=1)],
    obj: CreatePpapSubmission,
) -> ResponseSchemaModel[PpapSubmissionDetail]:
    return response_base.success(data=await supplier_lifecycle_service.create_ppap(db, application_id, obj))


@router.post(
    '/lifecycle/ppaps/{ppap_id}/submit',
    dependencies=[Depends(RequestPermission('erp:supplier:lifecycle:ppap')), DependsRBAC],
)
async def submit_ppap_submission(
    db: CurrentSessionTransaction, ppap_id: Annotated[int, Path(ge=1)]
) -> ResponseSchemaModel[PpapSubmissionDetail]:
    return response_base.success(data=await supplier_lifecycle_service.submit_ppap(db, ppap_id))


@router.post(
    '/lifecycle/ppaps/{ppap_id}/decision',
    dependencies=[Depends(RequestPermission('erp:supplier:lifecycle:approve')), DependsRBAC],
)
async def decide_ppap_submission(
    db: CurrentSessionTransaction,
    ppap_id: Annotated[int, Path(ge=1)],
    obj: DecidePpapSubmission,
) -> ResponseSchemaModel[PpapSubmissionDetail]:
    return response_base.success(data=await supplier_lifecycle_service.decide_ppap(db, ppap_id, obj))


@router.get('/lifecycle/avl', dependencies=lifecycle_view_dependencies)
async def list_supplier_avl(
    db: CurrentSession,
    supplier_id: Annotated[int | None, Query(ge=1)] = None,
    material_id: Annotated[int | None, Query(ge=1)] = None,
    status: Annotated[SupplierAvlStatus | None, Query()] = None,
) -> ResponseSchemaModel[list[ApprovedMaterialDetail]]:
    return response_base.success(data=await supplier_lifecycle_service.list_avl(db, supplier_id, material_id, status))


@router.get('/lifecycle/reviews', dependencies=lifecycle_view_dependencies)
async def list_periodic_reviews(
    db: CurrentSession,
    supplier_id: Annotated[int | None, Query(ge=1)] = None,
    status: Annotated[SupplierReviewStatus | None, Query()] = None,
) -> ResponseSchemaModel[list[PeriodicReviewDetail]]:
    return response_base.success(data=await supplier_lifecycle_service.list_reviews(db, supplier_id, status))


@router.post(
    '/lifecycle/avl/{avl_id}/reviews',
    dependencies=[Depends(RequestPermission('erp:supplier:lifecycle:review')), DependsRBAC],
)
async def create_periodic_review(
    db: CurrentSessionTransaction,
    avl_id: Annotated[int, Path(ge=1)],
    obj: CreatePeriodicReview,
) -> ResponseSchemaModel[PeriodicReviewDetail]:
    return response_base.success(data=await supplier_lifecycle_service.create_review(db, avl_id, obj))


@router.post(
    '/lifecycle/reviews/generate-due',
    dependencies=[Depends(RequestPermission('erp:supplier:lifecycle:review')), DependsRBAC],
)
async def generate_due_periodic_reviews(
    db: CurrentSessionTransaction,
) -> ResponseSchemaModel[list[PeriodicReviewDetail]]:
    return response_base.success(data=await supplier_lifecycle_service.generate_due_reviews(db))


@router.post(
    '/lifecycle/reviews/{review_id}/complete',
    dependencies=[Depends(RequestPermission('erp:supplier:lifecycle:review')), DependsRBAC],
)
async def complete_periodic_review(
    db: CurrentSessionTransaction,
    review_id: Annotated[int, Path(ge=1)],
    obj: CompletePeriodicReview,
) -> ResponseSchemaModel[PeriodicReviewDetail]:
    return response_base.success(data=await supplier_lifecycle_service.complete_review(db, review_id, obj))


@router.get('/category/tree', dependencies=view_dependencies)
async def get_category_tree(db: CurrentSession) -> ResponseSchemaModel[list[SupplierCategoryTreeNode]]:
    return response_base.success(data=await supplier_service.get_category_tree(db))


@router.get('/category', dependencies=view_dependencies)
async def list_categories(db: CurrentSession) -> ResponseSchemaModel[list[SupplierCategoryDetail]]:
    return response_base.success(data=await supplier_service.list_categories(db))


@router.post('/category', dependencies=[Depends(RequestPermission('erp:supplier:category')), DependsRBAC])
async def create_category(
    db: CurrentSessionTransaction, obj: CreateSupplierCategoryParam
) -> ResponseSchemaModel[SupplierCategoryDetail]:
    return response_base.success(data=await supplier_service.create_category(db, obj))


@router.put('/category/{category_id}', dependencies=[Depends(RequestPermission('erp:supplier:category')), DependsRBAC])
async def update_category(
    db: CurrentSessionTransaction,
    category_id: Annotated[int, Path(ge=1)],
    obj: UpdateSupplierCategoryParam,
) -> ResponseSchemaModel[SupplierCategoryDetail]:
    return response_base.success(data=await supplier_service.update_category(db, category_id, obj))


@router.put(
    '/category/{category_id}/status', dependencies=[Depends(RequestPermission('erp:supplier:category')), DependsRBAC]
)
async def update_category_status(
    db: CurrentSessionTransaction,
    category_id: Annotated[int, Path(ge=1)],
    obj: SupplierCategoryStatusParam,
) -> ResponseSchemaModel[SupplierCategoryDetail]:
    return response_base.success(data=await supplier_service.update_category_status(db, category_id, obj.status))


@router.get('/options', dependencies=view_dependencies)
async def supplier_options(
    db: CurrentSession,
    material_id: Annotated[int | None, Query(ge=1)] = None,
) -> ResponseSchemaModel[list[SupplierOption]]:
    return response_base.success(data=await supplier_service.supplier_options(db, material_id))


@router.get('', dependencies=[*view_dependencies, DependsPagination])
async def list_suppliers(
    db: CurrentSession,
    keyword: Annotated[str | None, Query()] = None,
    category_id: Annotated[int | None, Query(ge=1)] = None,
    status: Annotated[SupplierStatus | None, Query()] = None,
    cooperation_status: Annotated[CooperationStatus | None, Query()] = None,
    quality_status: Annotated[SupplierQualityStatus | None, Query()] = None,
    preferred: Annotated[bool | None, Query()] = None,
) -> ResponseSchemaModel[PageData[SupplierListItem]]:
    data = await supplier_service.list_suppliers(
        db, keyword, category_id, status, cooperation_status, quality_status, preferred
    )
    return response_base.success(data=data)


@router.get('/{supplier_id}', dependencies=view_dependencies)
async def get_supplier(
    db: CurrentSession, supplier_id: Annotated[int, Path(ge=1)]
) -> ResponseSchemaModel[SupplierDetail]:
    return response_base.success(data=await supplier_service.get_supplier(db, supplier_id))


@router.post('', dependencies=[Depends(RequestPermission('erp:supplier:config')), DependsRBAC])
async def create_supplier(db: CurrentSessionTransaction, obj: CreateSupplierParam) -> ResponseSchemaModel[SupplierDetail]:
    return response_base.success(data=await supplier_service.create_supplier(db, obj))


@router.put('/{supplier_id}', dependencies=[Depends(RequestPermission('erp:supplier:config')), DependsRBAC])
async def update_supplier(
    db: CurrentSessionTransaction,
    supplier_id: Annotated[int, Path(ge=1)],
    obj: UpdateSupplierParam,
) -> ResponseSchemaModel[SupplierDetail]:
    return response_base.success(data=await supplier_service.update_supplier(db, supplier_id, obj))


@router.put('/{supplier_id}/status', dependencies=[Depends(RequestPermission('erp:supplier:status')), DependsRBAC])
async def update_supplier_status(
    db: CurrentSessionTransaction,
    supplier_id: Annotated[int, Path(ge=1)],
    obj: SupplierStatusParam,
) -> ResponseSchemaModel[SupplierDetail]:
    return response_base.success(data=await supplier_service.update_supplier_status(db, supplier_id, obj.status))


@router.put(
    '/{supplier_id}/cooperation', dependencies=[Depends(RequestPermission('erp:supplier:cooperation')), DependsRBAC]
)
async def update_supplier_cooperation(
    db: CurrentSessionTransaction,
    supplier_id: Annotated[int, Path(ge=1)],
    obj: SupplierCooperationParam,
) -> ResponseSchemaModel[SupplierDetail]:
    return response_base.success(
        data=await supplier_service.update_supplier_cooperation(db, supplier_id, obj.cooperation_status)
    )


@router.put('/{supplier_id}/quality', dependencies=[Depends(RequestPermission('erp:supplier:quality')), DependsRBAC])
async def update_supplier_quality(
    db: CurrentSessionTransaction,
    supplier_id: Annotated[int, Path(ge=1)],
    obj: SupplierQualityParam,
) -> ResponseSchemaModel[SupplierDetail]:
    return response_base.success(data=await supplier_service.update_supplier_quality(db, supplier_id, obj.quality_status))


@router.get('/{supplier_id}/contacts', dependencies=view_dependencies)
async def list_contacts(
    db: CurrentSession, supplier_id: Annotated[int, Path(ge=1)]
) -> ResponseSchemaModel[list[SupplierContactDetail]]:
    return response_base.success(data=await supplier_service.list_contacts(db, supplier_id))


@router.post(
    '/{supplier_id}/contacts', dependencies=[Depends(RequestPermission('erp:supplier:contact')), DependsRBAC]
)
async def create_contact(
    db: CurrentSessionTransaction,
    supplier_id: Annotated[int, Path(ge=1)],
    obj: CreateSupplierContactParam,
) -> ResponseSchemaModel[SupplierContactDetail]:
    return response_base.success(data=await supplier_service.create_contact(db, supplier_id, obj))


@router.put('/contacts/{contact_id}', dependencies=[Depends(RequestPermission('erp:supplier:contact')), DependsRBAC])
async def update_contact(
    db: CurrentSessionTransaction,
    contact_id: Annotated[int, Path(ge=1)],
    obj: UpdateSupplierContactParam,
) -> ResponseSchemaModel[SupplierContactDetail]:
    return response_base.success(data=await supplier_service.update_contact(db, contact_id, obj))


@router.put(
    '/contacts/{contact_id}/primary', dependencies=[Depends(RequestPermission('erp:supplier:contact')), DependsRBAC]
)
async def set_contact_primary(
    db: CurrentSessionTransaction, contact_id: Annotated[int, Path(ge=1)]
) -> ResponseSchemaModel[SupplierContactDetail]:
    return response_base.success(data=await supplier_service.set_contact_primary(db, contact_id))


@router.put(
    '/contacts/{contact_id}/status', dependencies=[Depends(RequestPermission('erp:supplier:contact')), DependsRBAC]
)
async def update_contact_status(
    db: CurrentSessionTransaction,
    contact_id: Annotated[int, Path(ge=1)],
    obj: SupplierContactStatusParam,
) -> ResponseSchemaModel[SupplierContactDetail]:
    return response_base.success(data=await supplier_service.update_contact_status(db, contact_id, obj.status))


@router.get('/{supplier_id}/materials', dependencies=view_dependencies)
async def list_supplier_materials(
    db: CurrentSession, supplier_id: Annotated[int, Path(ge=1)]
) -> ResponseSchemaModel[list[SupplierMaterialDetail]]:
    return response_base.success(data=await supplier_service.list_supplier_materials(db, supplier_id))


@router.post(
    '/{supplier_id}/materials', dependencies=[Depends(RequestPermission('erp:supplier:material')), DependsRBAC]
)
async def create_supplier_material(
    db: CurrentSessionTransaction,
    supplier_id: Annotated[int, Path(ge=1)],
    obj: CreateSupplierMaterialParam,
) -> ResponseSchemaModel[SupplierMaterialDetail]:
    return response_base.success(data=await supplier_service.create_supplier_material(db, supplier_id, obj))


@router.put(
    '/materials/{relation_id}', dependencies=[Depends(RequestPermission('erp:supplier:material')), DependsRBAC]
)
async def update_supplier_material(
    db: CurrentSessionTransaction,
    relation_id: Annotated[int, Path(ge=1)],
    obj: UpdateSupplierMaterialParam,
) -> ResponseSchemaModel[SupplierMaterialDetail]:
    return response_base.success(data=await supplier_service.update_supplier_material(db, relation_id, obj))


@router.put(
    '/materials/{relation_id}/status', dependencies=[Depends(RequestPermission('erp:supplier:material')), DependsRBAC]
)
async def update_supplier_material_status(
    db: CurrentSessionTransaction,
    relation_id: Annotated[int, Path(ge=1)],
    obj: SupplierMaterialStatusParam,
) -> ResponseSchemaModel[SupplierMaterialDetail]:
    return response_base.success(data=await supplier_service.update_supplier_material_status(db, relation_id, obj.status))
