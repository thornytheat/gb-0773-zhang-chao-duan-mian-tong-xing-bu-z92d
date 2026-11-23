import csv
import io

from app.errors import TideError


def scan(text, header, source):
    records, issues = [], []
    reader = csv.reader(io.StringIO(text.lstrip('\ufeff'), newline=''), strict=True)
    segments = blanks = 0
    try:
        first = next(reader, None)
        if first is None:
            raise TideError('EMPTY_FILE', f'{source} 是空文件')
        if not any(first) and not text.strip('\ufeff \t\r\n,'):
            raise TideError('BLANK_FILE', f'{source} 只有空行')
        if len(first) != len(header) or set(first) != set(header):
            raise TideError('BAD_HEADER', f'{source} 表头与字段定义不符')
        segments = 1
        for fields in reader:
            line = reader.line_num
            if not any(value.strip() for value in fields):
                blanks += 1
            elif fields == first:
                segments += 1
            elif len(fields) != len(first):
                issues.append(dict(source=source, line=line, code='COLUMN_COUNT', raw=fields))
            else:
                records.append(dict(line=line, raw=dict(zip(first, fields))))
    except csv.Error as exc:
        raise TideError('BAD_CSV', f'{source} 第 {reader.line_num} 行引号错误') from exc
    if not records and not issues:
        code = 'BLANK_ROWS' if blanks else 'HEADER_ONLY'
        raise TideError(code, f'{source} 缺少数据行')
    return records, issues, segments, blanks
