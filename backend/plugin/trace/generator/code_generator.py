import re

from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.common.exception import errors
from backend.plugin.material.model import Material
from backend.plugin.trace.enums import SequenceResetType
from backend.plugin.trace.model import TraceCodeRule
from backend.plugin.trace.repository.trace import trace_repo
from backend.utils.timezone import timezone


TOKEN_PATTERN = re.compile(r'\{([A-Z_]+)\}')
SUPPORTED_TOKENS = {'YYYY', 'YY', 'MM', 'DD', 'YYYYMMDD', 'MATERIAL', 'MATERIAL_CODE', 'SEQ'}


class TraceCodeGenerator:
    """Renders code patterns and atomically reserves database-backed sequence ranges."""

    @staticmethod
    def validate_pattern(pattern: str) -> None:
        tokens = set(TOKEN_PATTERN.findall(pattern))
        if not tokens.issubset(SUPPORTED_TOKENS) or '{' in TOKEN_PATTERN.sub('', pattern) or '}' in TOKEN_PATTERN.sub('', pattern):
            raise errors.RequestError(msg='TRACE_PATTERN_INVALID')
        if 'SEQ' not in tokens:
            raise errors.RequestError(msg='TRACE_PATTERN_INVALID: {SEQ} is required')

    @staticmethod
    def sequence_key(reset_type: SequenceResetType, now: datetime) -> str:
        if reset_type == SequenceResetType.NEVER:
            return 'GLOBAL'
        if reset_type == SequenceResetType.YEARLY:
            return now.strftime('%Y')
        if reset_type == SequenceResetType.MONTHLY:
            return now.strftime('%Y%m')
        return now.strftime('%Y%m%d')

    @staticmethod
    def render(
        pattern: str,
        sequence_length: int,
        sequence: int,
        *,
        material: Material | None,
        now: datetime,
        prefix: str | None = None,
    ) -> str:
        TraceCodeGenerator.validate_pattern(pattern)
        if ('{MATERIAL}' in pattern or '{MATERIAL_CODE}' in pattern) and material is None:
            raise errors.RequestError(msg='TRACE_PATTERN_MATERIAL_REQUIRED')
        values = {
            'YYYY': now.strftime('%Y'),
            'YY': now.strftime('%y'),
            'MM': now.strftime('%m'),
            'DD': now.strftime('%d'),
            'YYYYMMDD': now.strftime('%Y%m%d'),
            'MATERIAL': material.material_code if material else '',
            'MATERIAL_CODE': material.material_code if material else '',
            'SEQ': f'{sequence:0{sequence_length}d}',
        }
        result = TOKEN_PATTERN.sub(lambda match: values[match.group(1)], pattern)
        return f'{prefix or ""}{result}'

    async def preview(
        self,
        pattern: str,
        sequence_length: int,
        *,
        material: Material | None = None,
        prefix: str | None = None,
        now: datetime | None = None,
    ) -> str:
        return self.render(
            pattern,
            sequence_length,
            1,
            material=material,
            now=now or timezone.now(),
            prefix=prefix,
        )

    async def _reserve_sequence_range(
        self,
        db: AsyncSession,
        rule_id: int,
        sequence_key: str,
        quantity: int,
    ) -> list[int]:
        sequence = await trace_repo.get_sequence_for_update(db, rule_id, sequence_key)
        if sequence is None:
            try:
                async with db.begin_nested():
                    await trace_repo.create_sequence(db, rule_id, sequence_key, quantity)
            except IntegrityError:
                sequence = await trace_repo.get_sequence_for_update(db, rule_id, sequence_key)
                if sequence is None:
                    raise errors.RequestError(msg='TRACE_SEQUENCE_GENERATION_FAILED')
            else:
                return list(range(1, quantity + 1))

        start = sequence.current_value + 1
        sequence.current_value += quantity
        await db.flush()
        return list(range(start, start + quantity))

    async def generate(
        self,
        db: AsyncSession,
        rule: TraceCodeRule,
        material: Material,
        quantity: int,
        *,
        now: datetime | None = None,
    ) -> list[str]:
        now = now or timezone.now()
        self.validate_pattern(rule.pattern)
        sequence_key = self.sequence_key(rule.sequence_reset_type, now)
        sequences = await self._reserve_sequence_range(db, rule.id, sequence_key, quantity)
        return [
            self.render(
                rule.pattern,
                rule.sequence_length,
                sequence,
                material=material,
                now=now,
                prefix=rule.prefix,
            )
            for sequence in sequences
        ]


trace_code_generator = TraceCodeGenerator()
