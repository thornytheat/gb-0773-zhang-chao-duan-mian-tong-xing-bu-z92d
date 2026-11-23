import re
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from fractions import Fraction

EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
STAMP = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})\Z')


def moment(value):
    value = value.strip()
    if not STAMP.fullmatch(value):
        raise ValueError('须提供带偏移的整秒时间')
    delta = datetime.fromisoformat(value).astimezone(UTC) - EPOCH
    return delta.days * 86400 + delta.seconds


def depth(value):
    value = value.strip()
    if not re.fullmatch(r'[+-]?\d{1,7}(?:\.\d{1,6})?', value):
        raise ValueError('水位小数格式错误')
    try:
        return Fraction(Decimal(value))
    except InvalidOperation as exc:
        raise ValueError('水位小数格式错误') from exc


def instant(value):
    fraction = Fraction(value)
    whole = fraction.numerator // fraction.denominator
    iso = (EPOCH + timedelta(seconds=whole)).isoformat().replace('+00:00', 'Z')
    tail = fraction - whole
    return f'{iso} + {tail}s' if tail else iso
