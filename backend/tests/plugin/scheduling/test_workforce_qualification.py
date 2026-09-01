from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from backend.plugin.scheduling.api.v1.mes.workforce import router
from backend.plugin.scheduling.enums import ConfigStatus
from backend.plugin.scheduling.model import (
    JobType,
    PositionQualificationRule,
    SkillLevel,
    WorkerAuthorization,
    WorkerCertificate,
    WorkerRoster,
    WorkerSkill,
)
from backend.plugin.scheduling.schema.workforce import PositionRuleInput, WorkerCertificateInput
from backend.plugin.scheduling.service.workforce_service import WorkforceService
from backend.utils.timezone import timezone


def test_workforce_models_registered() -> None:
    assert JobType.__tablename__ == 'mes_job_type'
    assert SkillLevel.__tablename__ == 'mes_skill_level'
    assert WorkerSkill.__tablename__ == 'mes_worker_skill'
    assert WorkerCertificate.__tablename__ == 'mes_worker_certificate'
    assert PositionQualificationRule.__tablename__ == 'mes_position_qualification_rule'
    assert WorkerAuthorization.__tablename__ == 'mes_worker_authorization'
    assert WorkerRoster.__tablename__ == 'mes_worker_roster'


def test_workforce_route_surface() -> None:
    paths = {route.path for route in router.routes}
    assert '/dashboard' in paths
    assert '/job-types' in paths
    assert '/skill-levels' in paths
    assert '/skills' in paths
    assert '/certificates' in paths
    assert '/rules' in paths
    assert '/authorizations' in paths
    assert '/rosters' in paths
    assert '/access-check' in paths


def test_rule_requires_operation_or_work_center() -> None:
    with pytest.raises(ValidationError):
        PositionRuleInput(
            rule_code='EMPTY',
            rule_name='Empty scope',
            job_type_id=1,
            minimum_skill_level_id=1,
        )


def test_certificate_date_order_and_validity_state() -> None:
    today = timezone.now().date()
    with pytest.raises(ValidationError):
        WorkerCertificateInput(
            user_id=1,
            certificate_type='forklift',
            certificate_name='Forklift',
            certificate_no='CERT-1',
            issued_on=today,
            valid_from=today,
            expires_on=today - timedelta(days=1),
        )
    row = WorkerCertificate(
        user_id=1,
        certificate_type='FORKLIFT',
        certificate_name='Forklift',
        certificate_no='CERT-2',
        issued_on=today - timedelta(days=365),
        valid_from=today - timedelta(days=365),
        expires_on=today + timedelta(days=10),
        status='ACTIVE',
    )
    row.id = 1
    row.created_time = timezone.now()
    assert WorkforceService._certificate_detail(row).validity_state == 'EXPIRING'


def test_rule_normalizes_codes() -> None:
    rule = PositionRuleInput(
        rule_code=' weld-01 ',
        rule_name='Welder',
        job_type_id=1,
        minimum_skill_level_id=1,
        operation_id=2,
        required_certificate_type=' weld-cert ',
        status=ConfigStatus.ACTIVE,
    )
    assert rule.rule_code == 'WELD-01'
    assert rule.required_certificate_type == 'WELD-CERT'
