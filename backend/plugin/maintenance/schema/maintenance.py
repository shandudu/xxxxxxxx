from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import ConfigDict, Field, field_validator, model_validator

from backend.common.schema import SchemaBase
from backend.plugin.maintenance.enums import (
    CycleUnit,
    DowntimeCategory,
    DowntimeSourceType,
    DowntimeStatus,
    FaultLevel,
    MaintenancePlanType,
    PlanStatus,
    RepairStatus,
    TaskResult,
    TaskStatus,
)
from backend.utils.timezone import timezone


CODE_PATTERN = r'^[A-Za-z0-9_.-]+$'


def normalize_code(value: Any) -> str:
    return str(value).strip().upper()


def optional_text(value: Any) -> str | None:
    if value is None:
        return None
    result = str(value).strip()
    return result or None


def aware(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.tz_info)
    return value


class MaintenancePlanBase(SchemaBase):
    plan_no: str | None = Field(default=None, max_length=100, pattern=CODE_PATTERN)
    plan_name: str = Field(min_length=1, max_length=200)
    equipment_id: int = Field(ge=1)
    work_center_id: int | None = Field(default=None, ge=1)
    plan_type: MaintenancePlanType
    cycle_unit: CycleUnit = CycleUnit.MONTH
    cycle_value: int = Field(default=1, ge=1, le=999)
    next_due_date: date
    lead_days: int = Field(default=0, ge=0, le=365)
    estimated_minutes: int = Field(default=30, ge=1, le=10080)
    requires_shutdown: bool = False
    assigned_user_id: int | None = Field(default=None, ge=1)
    checklist_items: list[str] = Field(default_factory=list, max_length=200)
    remark: str | None = Field(default=None, max_length=2000)

    @field_validator('plan_no', mode='before')
    @classmethod
    def normalize_plan_no(cls, value: Any) -> str | None:
        return normalize_code(value) if value else None

    @field_validator('plan_name', mode='before')
    @classmethod
    def normalize_plan_name(cls, value: Any) -> str:
        return str(value).strip()

    @field_validator('checklist_items', mode='before')
    @classmethod
    def normalize_checklist(cls, value: Any) -> list[str]:
        if value is None:
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    @field_validator('remark', mode='before')
    @classmethod
    def normalize_plan_remark(cls, value: Any) -> str | None:
        return optional_text(value)


class CreateMaintenancePlan(MaintenancePlanBase):
    pass


class UpdateMaintenancePlan(MaintenancePlanBase):
    status: PlanStatus = PlanStatus.ACTIVE


class MaintenancePlanDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plan_no: str
    plan_name: str
    equipment_id: int
    equipment_code: str = ''
    equipment_name: str = ''
    work_center_id: int | None = None
    work_center_name: str | None = None
    plan_type: MaintenancePlanType
    cycle_unit: CycleUnit
    cycle_value: int
    next_due_date: date
    lead_days: int
    estimated_minutes: int
    requires_shutdown: bool
    assigned_user_id: int | None = None
    assigned_username: str | None = None
    checklist_items: list[str] = Field(default_factory=list)
    status: PlanStatus
    last_generated_date: date | None = None
    remark: str | None = None
    created_time: datetime
    updated_time: datetime | None = None


class GenerateDueTasks(SchemaBase):
    through_date: date
    max_tasks: int = Field(default=500, ge=1, le=5000)


class StartTask(SchemaBase):
    started_at: datetime | None = None

    @field_validator('started_at', mode='after')
    @classmethod
    def normalize_started_at(cls, value: datetime | None) -> datetime | None:
        return aware(value)


class CompleteTask(SchemaBase):
    result: TaskResult
    checklist_results: list[dict[str, Any]] = Field(default_factory=list)
    findings: str | None = Field(default=None, max_length=4000)
    action_taken: str | None = Field(default=None, max_length=4000)
    create_repair_on_fail: bool = True
    completed_at: datetime | None = None
    remark: str | None = Field(default=None, max_length=2000)

    @field_validator('findings', 'action_taken', 'remark', mode='before')
    @classmethod
    def normalize_task_text(cls, value: Any) -> str | None:
        return optional_text(value)

    @field_validator('completed_at', mode='after')
    @classmethod
    def normalize_completed_at(cls, value: datetime | None) -> datetime | None:
        return aware(value)


class MaintenanceTaskDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_no: str
    plan_id: int
    plan_name: str = ''
    equipment_id: int
    equipment_code: str = ''
    equipment_name: str = ''
    work_center_id: int | None = None
    work_center_name: str | None = None
    task_type: MaintenancePlanType
    due_date: date
    assigned_user_id: int | None = None
    assigned_username: str | None = None
    estimated_minutes: int
    requires_shutdown: bool
    checklist_items: list[str] = Field(default_factory=list)
    checklist_results: list[dict[str, Any]] = Field(default_factory=list)
    status: TaskStatus
    result: TaskResult | None = None
    overdue: bool = False
    started_at: datetime | None = None
    completed_at: datetime | None = None
    downtime_id: int | None = None
    findings: str | None = None
    action_taken: str | None = None
    remark: str | None = None
    created_time: datetime


class CreateRepairOrder(SchemaBase):
    repair_no: str | None = Field(default=None, max_length=100, pattern=CODE_PATTERN)
    equipment_id: int = Field(ge=1)
    work_center_id: int | None = Field(default=None, ge=1)
    fault_level: FaultLevel = FaultLevel.MINOR
    fault_description: str = Field(min_length=1, max_length=4000)
    reported_at: datetime | None = None
    assigned_user_id: int | None = Field(default=None, ge=1)
    affects_capacity: bool = True
    remark: str | None = Field(default=None, max_length=2000)

    @field_validator('repair_no', mode='before')
    @classmethod
    def normalize_repair_no(cls, value: Any) -> str | None:
        return normalize_code(value) if value else None

    @field_validator('fault_description', mode='before')
    @classmethod
    def normalize_fault(cls, value: Any) -> str:
        return str(value).strip()

    @field_validator('remark', mode='before')
    @classmethod
    def normalize_repair_remark(cls, value: Any) -> str | None:
        return optional_text(value)

    @field_validator('reported_at', mode='after')
    @classmethod
    def normalize_reported_at(cls, value: datetime | None) -> datetime | None:
        return aware(value)


class AssignRepair(SchemaBase):
    assigned_user_id: int = Field(ge=1)


class StartRepair(SchemaBase):
    started_at: datetime | None = None

    @field_validator('started_at', mode='after')
    @classmethod
    def normalize_repair_start(cls, value: datetime | None) -> datetime | None:
        return aware(value)


class CompleteRepair(SchemaBase):
    root_cause: str = Field(min_length=1, max_length=4000)
    repair_action: str = Field(min_length=1, max_length=4000)
    spare_parts_used: str | None = Field(default=None, max_length=4000)
    repair_cost: Decimal = Field(default=Decimal('0'), ge=0, max_digits=18, decimal_places=4)
    completed_at: datetime | None = None
    remark: str | None = Field(default=None, max_length=2000)

    @field_validator('root_cause', 'repair_action', mode='before')
    @classmethod
    def normalize_required_repair_text(cls, value: Any) -> str:
        return str(value).strip()

    @field_validator('spare_parts_used', 'remark', mode='before')
    @classmethod
    def normalize_optional_repair_text(cls, value: Any) -> str | None:
        return optional_text(value)

    @field_validator('completed_at', mode='after')
    @classmethod
    def normalize_repair_completed_at(cls, value: datetime | None) -> datetime | None:
        return aware(value)


class RepairOrderDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    repair_no: str
    equipment_id: int
    equipment_code: str = ''
    equipment_name: str = ''
    work_center_id: int | None = None
    work_center_name: str | None = None
    fault_level: FaultLevel
    fault_description: str
    reported_at: datetime
    assigned_user_id: int | None = None
    assigned_username: str | None = None
    status: RepairStatus
    affects_capacity: bool
    downtime_id: int | None = None
    reported_by: int | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    root_cause: str | None = None
    repair_action: str | None = None
    spare_parts_used: str | None = None
    repair_cost: Decimal
    remark: str | None = None
    created_time: datetime


class CreateDowntime(SchemaBase):
    downtime_no: str | None = Field(default=None, max_length=100, pattern=CODE_PATTERN)
    equipment_id: int = Field(ge=1)
    work_center_id: int | None = Field(default=None, ge=1)
    category: DowntimeCategory
    source_type: DowntimeSourceType = DowntimeSourceType.MANUAL
    source_id: int | None = Field(default=None, ge=1)
    start_at: datetime
    end_at: datetime | None = None
    affects_capacity: bool = True
    reason: str | None = Field(default=None, max_length=4000)
    remark: str | None = Field(default=None, max_length=2000)

    @field_validator('downtime_no', mode='before')
    @classmethod
    def normalize_downtime_no(cls, value: Any) -> str | None:
        return normalize_code(value) if value else None

    @field_validator('reason', 'remark', mode='before')
    @classmethod
    def normalize_downtime_text(cls, value: Any) -> str | None:
        return optional_text(value)

    @field_validator('start_at', 'end_at', mode='after')
    @classmethod
    def normalize_downtime_datetime(cls, value: datetime | None) -> datetime | None:
        return aware(value)

    @model_validator(mode='after')
    def validate_range(self) -> 'CreateDowntime':
        if self.end_at and self.end_at <= self.start_at:
            raise ValueError('end_at must be after start_at')
        return self


class CloseDowntime(SchemaBase):
    end_at: datetime | None = None
    remark: str | None = Field(default=None, max_length=2000)

    @field_validator('end_at', mode='after')
    @classmethod
    def normalize_end_at(cls, value: datetime | None) -> datetime | None:
        return aware(value)

    @field_validator('remark', mode='before')
    @classmethod
    def normalize_close_remark(cls, value: Any) -> str | None:
        return optional_text(value)


class DowntimeDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    downtime_no: str
    equipment_id: int
    equipment_code: str = ''
    equipment_name: str = ''
    work_center_id: int | None = None
    work_center_name: str | None = None
    category: DowntimeCategory
    source_type: DowntimeSourceType
    source_id: int | None = None
    start_at: datetime
    end_at: datetime | None = None
    status: DowntimeStatus
    affects_capacity: bool
    reason: str | None = None
    duration_minutes: Decimal | None = None
    remark: str | None = None
    created_time: datetime


class MaintenanceDashboard(SchemaBase):
    active_plans: int
    pending_tasks: int
    overdue_tasks: int
    in_progress_tasks: int
    open_repairs: int
    critical_repairs: int
    open_downtimes: int
    downtime_minutes_30d: Decimal
    completion_rate_30d: Decimal
