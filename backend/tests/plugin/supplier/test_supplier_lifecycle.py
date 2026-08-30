import pytest
from pydantic import ValidationError

from backend.plugin.supplier.api.v1.erp.supplier import router
from backend.plugin.supplier.enums import SupplierAuditType, SupplierReviewDecision
from backend.plugin.supplier.model import (
    SupplierApprovedMaterial,
    SupplierPeriodicReview,
    SupplierPpapSubmission,
    SupplierQualificationApplication,
    SupplierQualificationAudit,
    SupplierSampleApproval,
)
from backend.plugin.supplier.schema.lifecycle import (
    CompletePeriodicReview,
    CreatePpapSubmission,
    CreateQualificationApplication,
)


def test_supplier_lifecycle_models_and_routes_are_registered() -> None:
    assert SupplierQualificationApplication.__tablename__ == 'erp_supplier_qualification_application'
    assert SupplierQualificationAudit.__tablename__ == 'erp_supplier_qualification_audit'
    assert SupplierSampleApproval.__tablename__ == 'erp_supplier_sample_approval'
    assert SupplierPpapSubmission.__tablename__ == 'erp_supplier_ppap_submission'
    assert SupplierApprovedMaterial.__tablename__ == 'erp_supplier_approved_material'
    assert SupplierPeriodicReview.__tablename__ == 'erp_supplier_periodic_review'
    paths = {route.path for route in router.routes}
    assert len(router.routes) == 43
    assert '/lifecycle/applications/{application_id}/approve' in paths
    assert '/lifecycle/ppaps/{ppap_id}/decision' in paths
    assert '/lifecycle/reviews/{review_id}/complete' in paths


def test_supplier_lifecycle_payload_validation() -> None:
    application = CreateQualificationApplication(
        supplier_id=1,
        requested_scope='Raw material supply',
        certificate_manifest={'business_license': 'LIC-001'},
    )
    assert application.supplier_id == 1
    assert SupplierAuditType.INITIAL == 'INITIAL'
    review = CompletePeriodicReview(
        decision=SupplierReviewDecision.CONTINUE,
        notes='Continue approved supplier relationship',
    )
    assert review.next_review_days == 365
    with pytest.raises(ValidationError):
        CreatePpapSubmission(
            material_id=1,
            level=6,
            version='1.0',
            document_manifest={},
        )
