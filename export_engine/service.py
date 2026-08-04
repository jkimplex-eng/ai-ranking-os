import csv
import json
from collections.abc import Iterator
from io import StringIO
from tempfile import SpooledTemporaryFile
from typing import Any, BinaryIO

from analytics.schemas import AnalyticsFilter, FilterOperator
from export_engine.repository import ExportRepository, ExportRow
from export_engine.schemas import ExportDescriptor, ExportFormat, ExportRequest


class ExportColumnNotFoundError(ValueError):
    pass


class ExportArtifact:
    def __init__(
        self,
        descriptor: ExportDescriptor,
        chunks: Iterator[bytes],
    ) -> None:
        self.descriptor = descriptor
        self.chunks = chunks


class ExportService:
    MEDIA_TYPES = {
        ExportFormat.CSV: ("text/csv; charset=utf-8", "csv"),
        ExportFormat.JSON: ("application/json", "json"),
        ExportFormat.XLSX: (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "xlsx",
        ),
        ExportFormat.PARQUET: ("application/vnd.apache.parquet", "parquet"),
    }

    def __init__(self, repository: ExportRepository) -> None:
        self.repository = repository

    def export(self, request: ExportRequest) -> ExportArtifact:
        source_rows = list(self.repository.rows(request.analytics_run_ids))
        rows = [row for row in source_rows if self._matches(row, request.filters)]
        available = sorted({key for row in source_rows for key in row})
        missing = set(request.columns) - set(available)
        if missing:
            raise ExportColumnNotFoundError(f"Unknown columns: {', '.join(sorted(missing))}")
        columns = request.columns or available
        selected = [{column: row.get(column) for column in columns} for row in rows]
        media_type, extension = self.MEDIA_TYPES[request.format]
        descriptor = ExportDescriptor(
            media_type=media_type,
            extension=extension,
            row_count=len(selected),
            columns=columns,
        )
        serializers = {
            ExportFormat.CSV: self._csv,
            ExportFormat.JSON: self._json,
            ExportFormat.XLSX: self._xlsx,
            ExportFormat.PARQUET: self._parquet,
        }
        return ExportArtifact(
            descriptor, serializers[request.format](selected, columns, request.batch_size)
        )

    def _csv(self, rows: list[ExportRow], columns: list[str], batch_size: int) -> Iterator[bytes]:
        buffer = StringIO(newline="")
        writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        yield b"\xef\xbb\xbf" + self._drain(buffer)
        for index, row in enumerate(rows, start=1):
            writer.writerow({key: self._safe_cell(value) for key, value in row.items()})
            if index % batch_size == 0:
                yield self._drain(buffer)
        remainder = self._drain(buffer)
        if remainder:
            yield remainder

    @staticmethod
    def _json(rows: list[ExportRow], columns: list[str], batch_size: int) -> Iterator[bytes]:
        del columns, batch_size
        yield b"["
        for index, row in enumerate(rows):
            if index:
                yield b","
            yield json.dumps(row, ensure_ascii=False, separators=(",", ":"), default=str).encode()
        yield b"]"

    def _xlsx(self, rows: list[ExportRow], columns: list[str], batch_size: int) -> Iterator[bytes]:
        del batch_size
        from openpyxl import Workbook

        # Ownership transfers to _file_chunks, which closes after streaming.
        temporary = SpooledTemporaryFile(max_size=8 * 1024 * 1024, mode="w+b")  # noqa: SIM115
        workbook = Workbook(write_only=True)
        sheet = workbook.create_sheet("Analytics")
        sheet.append(columns)
        for row in rows:
            sheet.append([self._safe_cell(row.get(column)) for column in columns])
        workbook.save(temporary)
        temporary.seek(0)
        return self._file_chunks(temporary)

    @staticmethod
    def _parquet(rows: list[ExportRow], columns: list[str], batch_size: int) -> Iterator[bytes]:
        import pyarrow as pa
        import pyarrow.parquet as pq

        # Ownership transfers to _file_chunks, which closes after streaming.
        temporary = SpooledTemporaryFile(max_size=8 * 1024 * 1024, mode="w+b")  # noqa: SIM115
        writer = None
        try:
            batches = range(0, len(rows), batch_size) or [0]
            for start in batches:
                chunk = rows[start : start + batch_size]
                data = {column: [row.get(column) for row in chunk] for column in columns}
                table = pa.table(data)
                if writer is None:
                    writer = pq.ParquetWriter(temporary, table.schema)
                writer.write_table(table)
            if writer is None:
                table = pa.table({column: pa.array([], type=pa.string()) for column in columns})
                writer = pq.ParquetWriter(temporary, table.schema)
            writer.close()
        except Exception:
            if writer is not None:
                writer.close()
            temporary.close()
            raise
        temporary.seek(0)
        return ExportService._file_chunks(temporary)

    @staticmethod
    def _file_chunks(file: BinaryIO, size: int = 64 * 1024) -> Iterator[bytes]:
        try:
            while chunk := file.read(size):
                yield chunk
        finally:
            file.close()

    @staticmethod
    def _drain(buffer: StringIO) -> bytes:
        value = buffer.getvalue().encode("utf-8")
        buffer.seek(0)
        buffer.truncate(0)
        return value

    @staticmethod
    def _safe_cell(value: Any) -> Any:
        if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
            return "'" + value
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        return value

    @staticmethod
    def _matches(row: ExportRow, filters: list[AnalyticsFilter]) -> bool:
        for criterion in filters:
            actual = row.get(criterion.field)
            expected = criterion.value
            if criterion.operator is FilterOperator.EQ and actual != expected:
                return False
            if criterion.operator is FilterOperator.NE and actual == expected:
                return False
            match = actual in expected if isinstance(expected, list) else actual == expected
            if criterion.operator is FilterOperator.IN and not match:
                return False
            if criterion.operator is FilterOperator.NOT_IN and match:
                return False
            if (
                criterion.operator is FilterOperator.CONTAINS
                and str(expected).casefold() not in str(actual or "").casefold()
            ):
                return False
            if criterion.operator in {FilterOperator.GTE, FilterOperator.LTE}:
                if actual is None or isinstance(expected, list):
                    return False
                try:
                    if criterion.operator is FilterOperator.GTE and actual < expected:
                        return False
                    if criterion.operator is FilterOperator.LTE and actual > expected:
                        return False
                except TypeError:
                    return False
        return True
