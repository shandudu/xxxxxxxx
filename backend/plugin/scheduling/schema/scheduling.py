from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from pydantic import ConfigDict, Field, field_validator, model_validator

from backend.common.schema import SchemaBase
from backend.plugin.scheduling.enums import (
    ConfigStatus,
    DispatchStatus,
    OperationScheduleStatus,
    ScheduleStatus,
    SchedulingDirection,
)
from backend.utils.timezone import timezone


CODE_PATTERN = r'^[A-Za-z0-9_-]+$'


def normalize_code(value: Any) -> str:
    return str(value).strip().upper()


def normalize_text(value: Any) -> str:
    return str(value).strip()


def normalize_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    result = normalize_text(value)
    return result or None


def normalize_datetime(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.tz_info)
    return value


class ShiftBase(SchemaBase):
    shift_code: str = Field(min_length=1, max_length=50, pattern=CODE_PATTERN)
    shift_name: str = Field(min_length=1, max_length=100)
    start_time: time
    end_time: time
    spans_next_day: bool = False
    break_minutes: int = Field(default=0, ge=0, le=720)
    remark: str | None = Field(default=None, max_length=1000)

    @field_validator('shift_code', mode='before')
    @classmethod
    def normalize_shift_code(cls, value: Any) -> str:
        return normalize_code(value)

    @field_validator('shift_name', mode='before')
    @classmethod
    def normalize_shift_name(cls, value: Any) -> str:
        return normalize_text(value)

    @field_validator('remark', mode='before')
    @classmethod
    def normalize_remark(cls, value: Any) -> str | None:
        return normalize_optional_text(value)

    @model_validator(mode='after')
    def validate_shift_range(self) -> 'ShiftBase':
        if not self.spans_next_day and self.end_time <= self.start_time:
            raise ValueError('end_time must be after start_time when shift does not span the next day')
        start_minutes = self.start_time.hour * 60 + self.start_time.minute
        end_minutes = self.end_time.hour * 60 + self.end_time.minute
        gross = end_minutes - start_minutes + (1440 if self.spans_next_day else 0)
        if gross <= self.break_minutes:
            raise ValueError('break_minutes must be less than shift duration')
        return self


class CreateShift(ShiftBase):
    pass


class UpdateShift(ShiftBase):
    status: ConfigStatus = ConfigStatus.ACTIVE


class ShiftDetail(ShiftBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: ConfigStatus
    created_time: datetime
    updated_time: datetime | None = None


class CalendarBase(SchemaBase):
    calendar_code: str = Field(min_length=1, max_length=50, pattern=CODE_PATTERN)
    calendar_name: str = Field(min_length=1, max_length=100)
    weekday_mask: str = Field(default='1,2,3,4,5', pattern=r'^[1-7](,[1-7])*$')
    timezone_name: str = Field(default='Asia/Hong_Kong', min_length=1, max_length=64)
    default_shift_id: int | None = Field(default=None, ge=1)
    remark: str | None = Field(default=None, max_length=1000)

    @field_validator('calendar_code', mode='before')
    @classmethod
    def normalize_calendar_code(cls, value: Any) -> str:
        return normalize_code(value)

    @field_validator('calendar_name', 'timezone_name', mode='before')
    @classmethod
    def normalize_required_text(cls, value: Any) -> str:
        return normalize_text(value)

    @field_validator('weekday_mask', mode='before')
    @classmethod
    def normalize_weekdays(cls, value: Any) -> str:
        days = sorted({int(item) for item in str(value).split(',') if str(item).strip()})
        if not days or days[0] < 1 or days[-1] > 7:
            raise ValueError('weekday_mask must contain weekdays 1 through 7')
        return ','.join(str(item) for item in days)

    @field_validator('remark', mode='before')
    @classmethod
    def normalize_calendar_remark(cls, value: Any) -> str | None:
        return normalize_optional_text(value)


class CreateCalendar(CalendarBase):
    pass


class UpdateCalendar(CalendarBase):
    status: ConfigStatus = ConfigStatus.ACTIVE


class UpsertCalendarDay(SchemaBase):
    work_date: date
    is_working_day: bool = True
    shift_id: int | None = Field(default=None, ge=1)
    capacity_factor: Decimal = Field(default=Decimal('1'), ge=0, le=10, max_digits=8, decimal_places=4)
    remark: str | None = Field(default=None, max_length=1000)

    @field_validator('remark', mode='before')
    @classmethod
    def normalize_day_remark(cls, value: Any) -> str | None:
        return normalize_optional_text(value)


class AssignWorkCenterCalendar(SchemaBase):
    work_center_id: int = Field(ge=1)
    effective_from: date
    effective_to: date | None = None
    capacity_factor: Decimal = Field(default=Decimal('1'), gt=0, le=10, max_digits=8, decimal_places=4)
    priority: int = 0

    @model_validator(mode='after')
    def validate_effective_range(self) -> 'AssignWorkCenterCalendar':
        if self.effective_to and self.effective_to < self.effective_from:
            raise ValueError('effective_to must be greater than or equal to effective_from')
        return self


class CalendarDayDetail(UpsertCalendarDay):
    model_config = ConfigDict(from_attributes=True)

    id: int
    calendar_id: int


class WorkCenterCalendarDetail(AssignWorkCenterCalendar):
    model_config = ConfigDict(from_attributes=True)

    id: int
    calendar_id: int
    work_center_code: str = ''
    work_center_name: str = ''


class CalendarDetail(CalendarBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: ConfigStatus
    default_shift_name: str | None = None
    days: list[CalendarDayDetail] = Field(default_factory=list)
    assignments: list[WorkCenterCalendarDetail] = Field(default_factory=list)
    created_time: datetime
    updated_time: datetime | None = None


class WorkOrderCandidate(SchemaBase):
    id: int
    work_order_no: str
    product_code: str
    product_name: str
    planned_quantity: Decimal
    status: str
    operation_count: int
    planned_start_at: datetime | None = None
    planned_end_at: datetime | None = None


class CreateApsSchedule(SchemaBase):
    schedule_no: str | None = Field(default=None, max_length=100, pattern=CODE_PATTERN)
    schedule_name: str = Field(min_length=1, max_length=200)
    direction: SchedulingDirection = SchedulingDirection.FORWARD
    horizon_start_at: datetime
    horizon_end_at: datetime
    work_order_ids: list[int] = Field(min_length=1, max_length=500)
    include_queue_time: bool = True
    include_move_time: bool = True
    remark: str | None = Field(default=None, max_length=2000)

    @field_validator('schedule_no', mode='before')
    @classmethod
    def normalize_schedule_no(cls, value: Any) -> str | None:
        return normalize_code(value) if value else None

    @field_validator('schedule_name', mode='before')
    @classmethod
    def normalize_schedule_name(cls, value: Any) -> str:
        return normalize_text(value)

    @field_validator('remark', mode='before')
    @classmethod
    def normalize_schedule_remark(cls, value: Any) -> str | None:
        return normalize_optional_text(value)

    @field_validator('horizon_start_at', 'horizon_end_at', mode='after')
    @classmethod
    def normalize_horizon_datetime(cls, value: datetime) -> datetime:
        return normalize_datetime(value)  # type: ignore[return-value]

    @model_validator(mode='after')
    def validate_schedule(self) -> 'CreateApsSchedule':
        if self.horizon_end_at <= self.horizon_start_at:
            raise ValueError('horizon_end_at must be after horizon_start_at')
        if len(self.work_order_ids) != len(set(self.work_order_ids)):
            raise ValueError('work_order_ids must be unique')
        return self


class OperationScheduleDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    schedule_id: int
    work_order_id: int
    work_order_operation_id: int
    routing_operation_id: int | None = None
    operation_id: int
    work_center_id: int
    sequence_no: int
    lane_no: int
    planned_start_at: datetime
    planned_end_at: datetime
    planned_quantity: Decimal
    setup_minutes: Decimal
    run_minutes: Decimal
    queue_minutes: Decimal
    move_minutes: Decimal
    load_minutes: Decimal
    total_minutes: Decimal
    work_order_no_snapshot: str
    product_code_snapshot: str
    product_name_snapshot: str
    operation_code_snapshot: str
    operation_name_snapshot: str
    work_center_code_snapshot: str
    work_center_name_snapshot: str
    status: OperationScheduleStatus
    is_overdue: bool
    dispatch_count: int


class ApsScheduleListItem(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    schedule_no: str
    schedule_name: str
    direction: SchedulingDirection
    horizon_start_at: datetime
    horizon_end_at: datetime
    status: ScheduleStatus
    include_queue_time: bool
    include_move_time: bool
    work_order_count: int
    operation_count: int
    overdue_operation_count: int
    error_message: str | None = None
    started_at: datetime
    completed_at: datetime | None = None
    published_at: datetime | None = None
    remark: str | None = None
    created_time: datetime


class ApsScheduleDetail(ApsScheduleListItem):
    operations: list[OperationScheduleDetail] = Field(default_factory=list)


class WorkCenterLoad(SchemaBase):
    work_center_id: int
    work_center_code: str
    work_center_name: str
    parallel_capacity: int
    available_minutes: Decimal
    scheduled_load_minutes: Decimal
    utilization_rate: Decimal
    overload_minutes: Decimal
    operation_count: int


class CreateDispatch(SchemaBase):
    schedule_operation_id: int = Field(ge=1)
    dispatch_no: str | None = Field(default=None, max_length=100, pattern=CODE_PATTERN)
    assigned_user_id: int | None = Field(default=None, ge=1)
    team_id: int | None = Field(default=None, ge=1)
    workstation_id: int | None = Field(default=None, ge=1)
    assigned_team: str | None = Field(default=None, max_length=100)
    workstation_code: str | None = Field(default=None, max_length=100)
    dispatch_quantity: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=6)
    priority: int = Field(default=0, ge=-9999, le=9999)
    remark: str | None = Field(default=None, max_length=2000)

    @field_validator('dispatch_no', mode='before')
    @classmethod
    def normalize_dispatch_no(cls, value: Any) -> str | None:
        return normalize_code(value) if value else None

    @field_validator('assigned_team', 'workstation_code', 'remark', mode='before')
    @classmethod
    def normalize_dispatch_text(cls, value: Any) -> str | None:
        return normalize_optional_text(value)

    @model_validator(mode='after')
    def validate_assignment(self) -> 'CreateDispatch':
        if not any((self.assigned_user_id, self.team_id, self.workstation_id, self.assigned_team, self.workstation_code)):
            raise ValueError('assigned user, team or workstation is required')
        return self


class DispatchDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dispatch_no: str
    schedule_operation_id: int
    work_order_id: int
    work_order_operation_id: int
    work_center_id: int
    planned_start_at: datetime
    planned_end_at: datetime
    dispatch_quantity: Decimal
    priority: int
    status: DispatchStatus
    assigned_user_id: int | None = None
    team_id: int | None = None
    workstation_id: int | None = None
    production_execution_id: int | None = None
    assigned_team: str | None = None
    workstation_code: str | None = None
    dispatched_at: datetime | None = None
    accepted_at: datetime | None = None
    remark: str | None = None
    work_order_no: str = ''
    operation_name: str = ''
    work_center_name: str = ''
    assigned_username: str | None = None
    created_time: datetime
