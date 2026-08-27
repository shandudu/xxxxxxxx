from backend.common.enums import StrEnum


class DemoRunStatus(StrEnum):
    RUNNING = 'RUNNING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'
