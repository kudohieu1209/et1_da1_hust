from fastapi import APIRouter, HTTPException, Query

from app.services.program_catalog import program_catalog


router = APIRouter(prefix="/api/programs", tags=["Programs"])


@router.get("")
def list_programs(
    search: str | None = Query(None, description="Tìm theo mã, tên, viện hoặc ngôn ngữ."),
    supported_only: bool = Query(False, description="Chỉ hiện chương trình đã có CTĐT được kiểm chứng."),
):
    """Danh mục chương trình đại học từ nguồn tuyển sinh chính thức HUST."""

    programs = program_catalog.list(search=search, supported_only=supported_only)
    return {
        "source": program_catalog.source,
        "curriculum_sources_discovered_at": program_catalog.curriculum_sources_discovered_at,
        "total": len(programs),
        "programs": programs,
    }


@router.get("/{program_code}")
def get_program(program_code: str):
    program = program_catalog.get(program_code)
    if not program:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy chương trình {program_code.upper()}")
    return {
        "source": program_catalog.source,
        "curriculum_sources_discovered_at": program_catalog.curriculum_sources_discovered_at,
        "program": program,
    }
