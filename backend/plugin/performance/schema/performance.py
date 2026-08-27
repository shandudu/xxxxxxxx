from datetime import date, datetime
from decimal import Decimal

from pydantic import ConfigDict, Field, model_validator

from backend.common.schema import SchemaBase
from backend.plugin.performance.enums import MetricGrain, TargetStatus


class PerformanceTargetInput(SchemaBase):
    availability_target: Decimal = Field(default=Decimal('90'), ge=0, le=100, decimal_places=4)
    performance_target: Decimal = Field(default=Decimal('95'), ge=0, le=100, decimal_places=4)
    quality_target: Decimal = Field(default=Decimal('99'), ge=0, le=100, decimal_places=4)
    oee_target: Decimal = Field(default=Decimal('85'), ge=0, le=100, decimal_places=4)
    ideal_cycle_seconds: Decimal | None = Field(
        default=None, gt=0, max_digits=18, decimal_places=6
    )
    status: TargetStatus = TargetStatus.ACTIVE
    remark: str | None = Field(default=None, max_length=2000)


class PerformanceTargetDetail(PerformanceTargetInput):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    work_center_id: int
    work_center_code: str = ''
    work_center_name: str = ''
    configured: bool = False


class MetricValues(SchemaBase):
    calendar_minutes: Decimal
    planned_downtime_minutes: Decimal
    planned_production_minutes: Decimal
    unplanned_downtime_minutes: Decimal
    operating_minutes: Decimal
    actual_run_minutes: Decimal
    idle_capacity_minutes: Decimal
    good_quantity: Decimal
    scrap_quantity: Decimal
    total_quantity: Decimal
    ideal_run_minutes: Decimal
    availability_rate: Decimal
    performance_rate: Decimal
    quality_rate: Decimal
    oee_rate: Decimal
    utilization_rate: Decimal
    actual_cycle_seconds: Decimal | None
    ideal_cycle_seconds: Decimal | None
    throughput_per_hour: Decimal
    failure_count: int
    mtbf_minutes: Decimal | None
    mttr_minutes: Decimal | None
    source_execution_count: int


class PerformanceDashboard(MetricValues):
    period_start: date
    period_end: date
    work_center_count: int
    target_oee_rate: Decimal
    on_target_center_count: int


class WorkCenterPerformance(MetricValues):
    work_center_id: int
    work_center_code: str
    work_center_name: str
    parallel_capacity: int
    availability_target: Decimal
    performance_target: Decimal
    quality_target: Decimal
    oee_target: Decimal
    oee_on_target: bool


class PerformanceTrendPoint(MetricValues):
    period_start: date
    period_end: date


class EquipmentReliability(SchemaBase):
    equipment_id: int
    equipment_code: str
    equipment_name: str
    failure_count: int
    planned_downtime_minutes: Decimal
    unplanned_downtime_minutes: Decimal
    total_downtime_minutes: Decimal
    availability_rate: Decimal
    mtbf_minutes: Decimal | None
    mttr_minutes: Decimal | None
    last_failure_at: datetime | None


class CycleAnalysis(SchemaBase):
    work_center_id: int
    work_center_code: str
    work_center_name: str
    operation_id: int
    operation_code: str
    operation_name: str
    product_code: str
    product_name: str
    execution_count: int
    good_quantity: Decimal
    scrap_quantity: Decimal
    total_quantity: Decimal
    actual_run_minutes: Decimal
    ideal_run_minutes: Decimal
    actual_cycle_seconds: Decimal | None
    ideal_cycle_seconds: Decimal | None
    cycle_efficiency_rate: Decimal


class DowntimePareto(SchemaBase):
    rank: int
    reason: str
    event_count: int
    downtime_minutes: Decimal
    percentage: Decimal
    cumulative_percentage: Decimal


class RebuildSnapshots(SchemaBase):
    start_date: date
    end_date: date
    work_center_ids: list[int] = Field(default_factory=list, max_length=200)

    @model_validator(mode='after')
    def validate_period(self) -> 'RebuildSnapshots':
        if self.end_date < self.start_date:
            raise ValueError('end_date must not be before start_date')
        if (self.end_date - self.start_date).days > 92:
            raise ValueError('snapshot rebuild range must not exceed 93 days')
        if len(self.work_center_ids) != len(set(self.work_center_ids)):
            raise ValueError('work_center_ids must be unique')
        return self


class PerformanceSnapshotDetail(MetricValues):
    model_config = ConfigDict(from_attributes=True)

    id: int
    metric_date: date
    work_center_id: int
    work_center_code: str = ''
    work_center_name: str = ''
    calculated_at: datetime


class SnapshotRebuildResult(SchemaBase):
    start_date: date
    end_date: date
    work_center_count: int
    snapshot_count: int


__all__ = [
    'CycleAnalysis',
    'DowntimePareto',
    'EquipmentReliability',
    'MetricGrain',
    'PerformanceDashboard',
    'PerformanceSnapshotDetail',
    'PerformanceTargetDetail',
    'PerformanceTargetInput',
    'PerformanceTrendPoint',
    'RebuildSnapshots',
    'SnapshotRebuildResult',
    'WorkCenterPerformance',
]
