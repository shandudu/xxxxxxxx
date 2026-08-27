from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import ConfigDict, Field, field_validator, model_validator

from backend.common.schema import SchemaBase
from backend.plugin.scheduling.enums import DispatchStatus, ShopfloorStatus, TeamMemberRole, WorkstationSessionStatus


CODE_PATTERN = r'^[A-Za-z0-9_-]+$'


def _optional(value: Any) -> str | None:
    if value is None:
        return None
    return str(value).strip() or None


class TeamInput(SchemaBase):
    team_code: str = Field(min_length=1, max_length=80, pattern=CODE_PATTERN)
    team_name: str = Field(min_length=1, max_length=150)
    work_center_id: int | None = Field(default=None, ge=1)
    leader_user_id: int | None = Field(default=None, ge=1)
    status: ShopfloorStatus = ShopfloorStatus.ACTIVE
    remark: str | None = Field(default=None, max_length=1000)

    @field_validator('team_code', mode='before')
    @classmethod
    def code(cls, value: Any) -> str:
        return str(value).strip().upper()

    @field_validator('team_name', mode='before')
    @classmethod
    def name(cls, value: Any) -> str:
        return str(value).strip()

    @field_validator('remark', mode='before')
    @classmethod
    def optional(cls, value: Any) -> str | None:
        return _optional(value)


class TeamMemberInput(SchemaBase):
    user_id: int = Field(ge=1)
    member_role: TeamMemberRole = TeamMemberRole.OPERATOR
    remark: str | None = Field(default=None, max_length=1000)


class StatusInput(SchemaBase):
    status: ShopfloorStatus


class TeamMemberDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    team_id: int
    user_id: int
    username: str = ''
    nickname: str = ''
    member_role: TeamMemberRole
    status: ShopfloorStatus
    remark: str | None = None


class TeamDetail(TeamInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    work_center_code: str | None = None
    work_center_name: str | None = None
    leader_username: str | None = None
    members: list[TeamMemberDetail] = Field(default_factory=list)
    created_time: datetime


class WorkstationInput(SchemaBase):
    workstation_code: str = Field(min_length=1, max_length=80, pattern=CODE_PATTERN)
    workstation_name: str = Field(min_length=1, max_length=150)
    work_center_id: int = Field(ge=1)
    equipment_id: int | None = Field(default=None, ge=1)
    terminal_enabled: bool = True
    status: ShopfloorStatus = ShopfloorStatus.ACTIVE
    remark: str | None = Field(default=None, max_length=1000)

    @field_validator('workstation_code', mode='before')
    @classmethod
    def code(cls, value: Any) -> str:
        return str(value).strip().upper()


class WorkstationDetail(WorkstationInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    work_center_code: str = ''
    work_center_name: str = ''
    equipment_code: str | None = None
    equipment_name: str | None = None
    created_time: datetime


class WorkstationOption(SchemaBase):
    id: int
    code: str
    name: str
    work_center_id: int


class CheckInInput(SchemaBase):
    team_id: int | None = Field(default=None, ge=1)


class WorkstationSessionDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    workstation_id: int
    user_id: int
    team_id: int | None = None
    status: WorkstationSessionStatus
    signed_in_at: datetime
    last_activity_at: datetime
    signed_out_at: datetime | None = None


class TerminalDispatchDetail(SchemaBase):
    id: int
    dispatch_no: str
    work_order_id: int
    work_order_no: str
    work_order_operation_id: int
    operation_name: str
    dispatch_quantity: Decimal
    status: DispatchStatus
    planned_start_at: datetime
    planned_end_at: datetime
    assigned_team: str | None = None
    workstation_code: str | None = None
    production_execution_id: int | None = None


class TerminalContext(SchemaBase):
    workstation: WorkstationDetail
    session: WorkstationSessionDetail | None = None
    dispatches: list[TerminalDispatchDetail] = Field(default_factory=list)


class CompleteDispatchInput(SchemaBase):
    good_quantity: Decimal = Field(ge=0, max_digits=18, decimal_places=6)
    scrap_quantity: Decimal = Field(default=Decimal('0'), ge=0, max_digits=18, decimal_places=6)
    remark: str | None = Field(default=None, max_length=2000)

    @model_validator(mode='after')
    def quantity(self):
        if self.good_quantity + self.scrap_quantity <= 0:
            raise ValueError('completion quantity must be positive')
        return self


class UserOption(SchemaBase):
    id: int
    username: str
    nickname: str
