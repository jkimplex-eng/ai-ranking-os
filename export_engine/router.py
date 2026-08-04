from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.export_repository import PlatformExportRepository
from export_engine.repository import ExportSourceNotFoundError
from export_engine.schemas import ExportRequest
from export_engine.service import ExportColumnNotFoundError, ExportService

router = APIRouter(prefix="/exports", tags=["export"])
DbSession = Annotated[Session, Depends(get_db)]


def get_export_service(db: DbSession) -> ExportService:
    return ExportService(PlatformExportRepository(db))


Service = Annotated[ExportService, Depends(get_export_service)]


@router.post(
    "",
    response_class=StreamingResponse,
    responses={
        200: {
            "description": "Streaming export",
            "content": {
                "text/csv": {},
                "application/json": {},
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {},
                "application/vnd.apache.parquet": {},
            },
        }
    },
)
def export_analytics(payload: ExportRequest, service: Service) -> StreamingResponse:
    try:
        artifact = service.export(payload)
    except ExportSourceNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ExportColumnNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error
    descriptor = artifact.descriptor
    filename = f"{payload.filename}.{descriptor.extension}"
    return StreamingResponse(
        artifact.chunks,
        media_type=descriptor.media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Export-Row-Count": str(descriptor.row_count),
            "X-Export-Columns": str(len(descriptor.columns)),
        },
    )
