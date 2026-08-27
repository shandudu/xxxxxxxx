from decimal import Decimal

import pytest
from pydantic import ValidationError

from backend.plugin.scheduling.api.v1.mes.shopfloor import router
from backend.plugin.scheduling.enums import ShopfloorStatus, TeamMemberRole
from backend.plugin.scheduling.model import ApsDispatch, ProductionTeam, ProductionTeamMember, Workstation, WorkstationSession
from backend.plugin.scheduling.schema.shopfloor import CompleteDispatchInput, TeamInput, WorkstationInput
from backend.plugin.scheduling.schema.scheduling import CreateDispatch


def test_shopfloor_models_and_dispatch_links() -> None:
    assert ProductionTeam.__tablename__ == 'mes_production_team'
    assert ProductionTeamMember.__tablename__ == 'mes_production_team_member'
    assert Workstation.__tablename__ == 'mes_workstation'
    assert WorkstationSession.__tablename__ == 'mes_workstation_session'
    names = {constraint.name for constraint in ApsDispatch.__table__.foreign_key_constraints}
    assert {'fk_aps_dispatch_team', 'fk_aps_dispatch_workstation', 'fk_aps_dispatch_execution'} <= names


def test_shopfloor_route_surface() -> None:
    paths = {route.path for route in router.routes}
    assert '/teams' in paths
    assert '/workstations' in paths
    assert '/terminal/{workstation_id}/context' in paths
    assert '/terminal/{workstation_id}/dispatches/{dispatch_id}/start' in paths
    assert '/terminal/{workstation_id}/dispatches/{dispatch_id}/complete' in paths
    assert len(router.routes) == 17


def test_shopfloor_schemas() -> None:
    team = TeamInput(team_code='team-01', team_name='一班')
    station = WorkstationInput(workstation_code='ws-01', workstation_name='装配工位', work_center_id=1)
    dispatch = CreateDispatch(schedule_operation_id=1, team_id=1)
    assert team.team_code == 'TEAM-01'
    assert team.status == ShopfloorStatus.ACTIVE
    assert station.workstation_code == 'WS-01'
    assert dispatch.team_id == 1
    assert TeamMemberRole.OPERATOR == 'OPERATOR'
    with pytest.raises(ValidationError):
        CreateDispatch(schedule_operation_id=1)
    with pytest.raises(ValidationError):
        CompleteDispatchInput(good_quantity=Decimal('0'), scrap_quantity=Decimal('0'))
