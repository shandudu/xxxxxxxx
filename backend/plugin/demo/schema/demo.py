from datetime import datetime

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase
from backend.plugin.demo.enums import DemoRunStatus


class ManufacturingDemoRunDetail(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_no: str
    scenario_code: str
    status: DemoRunStatus
    started_at: datetime
    completed_at: datetime | None = None
    failed_step: str | None = None
    error_message: str | None = None


class ManufacturingDemoVerifyResult(SchemaBase):
    passed: bool
    completed_steps: list[str] = Field(default_factory=list)
    missing_steps: list[str] = Field(default_factory=list)
    references: dict[str, str] = Field(default_factory=dict)


class ManufacturingDemoStatus(SchemaBase):
    run: ManufacturingDemoRunDetail | None = None
    verification: ManufacturingDemoVerifyResult
