from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from app.services.data_loader import data_loader
from app.engine.rule_engine import rule_engine
from app.engine.graph_engine import graph_engine
from app.models.schemas import CheckEligibilityRequest, CheckEligibilityResponse, ImpactSimulationRequest, ImpactSimulationResponse

router = APIRouter(prefix="/api/courses", tags=["Courses & Rules"])

@router.get("/curriculum")
def get_active_curriculum():
    """Metadata, graduation formula and groups for the active student's CTĐT."""
    curriculum = data_loader.get_curriculum()
    return {
        "program": curriculum["program"],
        "graduation_paths": curriculum["graduation_paths"],
        "groups": curriculum["groups"],
        "non_credit_group_ids": curriculum["non_credit_group_ids"],
        "sources": curriculum["sources"],
    }

@router.get("")
def get_all_courses(
    category: Optional[str] = Query(None, description="Lọc theo loại môn (Bắt buộc, Tự chọn, GDTC...)"),
    semester: Optional[int] = Query(None, description="Lọc theo kỳ gợi ý (1-8)")
):
    courses = data_loader.get_all_courses()
    result = []
    for c in courses:
        code = c["code"]
        rule = data_loader.get_rule(code) or {}
        if category and c.get("category") != category:
            continue
        if semester is not None and c.get("suggested_semester") != semester:
            continue

        result.append({
            "code": code,
            "name": c["name"],
            "credits": c.get("credits", 0.0),
            "suggested_semester": c.get("suggested_semester"),
            "is_compulsory": c.get("is_compulsory", False),
            "category": c.get("category", ""),
            "modules": data_loader.get_course_modules(c),
            "department": c.get("department", ""),
            "raw_condition": rule.get("raw_condition", ""),
            "condition_tree": rule.get("condition_tree", []),
            "flat_prerequisites": rule.get("flat_prerequisites", []),
            "flat_prior_courses": rule.get("flat_prior_courses", []),
            "flat_corequisites": rule.get("flat_corequisites", []),
            "min_credits_accumulated": rule.get("min_credits_accumulated", 0)
        })

    return {"total": len(result), "courses": result}

@router.get("/graph/visualization")
def get_graph_data():
    """Lấy dữ liệu Nodes & Edges để trực quan hóa đồ thị cây môn học trên Frontend"""
    return graph_engine.get_graph_visualization_data()

@router.get("/{course_code}")
def get_course_detail(course_code: str):
    code = course_code.upper()
    graph_engine.ensure_current()
    course = data_loader.get_course(code)
    rule = data_loader.get_rule(code)

    if not course and not rule:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy môn học {code}")

    # Danh sách các môn mở khóa tiếp theo
    successors = []
    if graph_engine.graph.has_node(code):
        for s in graph_engine.graph.successors(code):
            s_node = graph_engine.graph.nodes[s]
            edge_data = graph_engine.graph.get_edge_data(code, s)
            successors.append({
                "code": s,
                "name": s_node.get("name", s),
                "credits": s_node.get("credits", 0.0),
                "type": edge_data.get("type", "PRIOR")
            })

    return {
        "code": code,
        "name": (course or rule).get("name", code),
        "credits": (course or rule).get("credits", 0.0),
        "suggested_semester": (course or rule).get("suggested_semester"),
        "is_compulsory": (course or rule).get("is_compulsory", False),
        "category": (course or rule).get("category", ""),
        "modules": data_loader.get_course_modules(course or rule),
        "raw_condition": (rule or {}).get("raw_condition", ""),
        "condition_tree": (rule or {}).get("condition_tree", []),
        "flat_prerequisites": (rule or {}).get("flat_prerequisites", []),
        "flat_prior_courses": (rule or {}).get("flat_prior_courses", []),
        "flat_corequisites": (rule or {}).get("flat_corequisites", []),
        "min_credits_accumulated": (rule or {}).get("min_credits_accumulated", 0),
        "unlocks_courses": successors
    }

@router.post("/check-eligibility", response_model=CheckEligibilityResponse)
def check_course_eligibility(req: CheckEligibilityRequest):
    code = req.course_code.upper()
    result = rule_engine.check_eligibility(
        code, 
        simulated_passed_codes=req.simulated_passed_codes
    )
    return CheckEligibilityResponse(**result)

@router.post("/simulate-impact", response_model=ImpactSimulationResponse)
def simulate_impact(req: ImpactSimulationRequest):
    code = req.failed_course_code.upper()
    result = graph_engine.get_impact_analysis(code)
    return ImpactSimulationResponse(**result)
