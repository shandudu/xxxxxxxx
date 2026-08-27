from enum import StrEnum


class CostPeriodStatus(StrEnum):
    OPEN = 'OPEN'
    CALCULATING = 'CALCULATING'
    CLOSED = 'CLOSED'


class CostPostingStatus(StrEnum):
    DRAFT = 'DRAFT'
    CALCULATED = 'CALCULATED'
    POSTED = 'POSTED'


class CostElement(StrEnum):
    MATERIAL = 'MATERIAL'
    LABOR = 'LABOR'
    MACHINE = 'MACHINE'
    OVERHEAD = 'OVERHEAD'
    QUALITY_LOSS = 'QUALITY_LOSS'


class MarginDimension(StrEnum):
    PRODUCT = 'PRODUCT'
    CUSTOMER = 'CUSTOMER'
