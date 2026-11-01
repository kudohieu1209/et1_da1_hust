"""Reproduce source-based resolutions without changing the original extractions.

The reviewed source files are committed alongside the small review manifest.
No LLM, private archive, database or network is needed to rebuild the datasets.
"""
from __future__ import annotations

import copy
import hashlib
import itertools
import json
from pathlib import Path

from import_official_curricula import build_dataset, load_catalog, output_name
from validate_curriculum import validate_curriculum

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
REVIEWER = "source-review-20261101"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def merge_choices(raw, strategy):
    """Enumerate legal bundles rather than treating separate choices as one."""
    modules = [g for g in raw["groups"] if g["kind"] == "module" and g["counts_toward_degree"]]
    if strategy == "language_and_specialization":
        pairs = itertools.product(
            [g for g in modules if g["required_credits"] == 10],
            [g for g in modules if g["required_credits"] == 15],
        )
    elif strategy == "materials_core_and_specialization":
        core = [g for g in modules if g["required_credits"] == 10]
        specialized = [g for g in modules if g["required_credits"] == 16]
        pairs = [(core[1] if "2.1:" in g["name"] else core[0], g) for g in specialized]
    else:
        raise ValueError(f"Unknown choice strategy: {strategy}")
    bundles = []
    for pair in pairs:
        courses = {c["code"]: c for group in pair for c in group["courses"]}
        bundles.append({
            "name": " + ".join(g["name"] for g in pair), "kind": "module",
            "required_credits": sum(g["required_credits"] for g in pair),
            "counts_toward_degree": True, "courses": list(courses.values()),
        })
    if len(bundles) != 6:
        raise ValueError("Expected six source-defined bundles; review the source changes.")
    raw["groups"] = [g for g in raw["groups"] if g not in modules] + bundles


def convert_ev2(extraction):
    groups = []
    for g in extraction["knowledge_blocks"]:
        # g008 is the parent heading, not an additional 16-credit requirement.
        if g["id"] == "g008" or g.get("degree_scope") != "bachelor":
            continue
        courses = [c for c in extraction["courses"] if c["block_id"] == g["id"]]
        groups.append({
            "name": g["name"], "kind": "module" if g["id"] in {"g009", "g010"} else "block",
            "required_credits": g["minimum_credits"],
            "counts_toward_degree": g["counts_toward_degree_credits"],
            "courses": [{"code": c["code"], "name": c["name"], "credits": c.get("degree_credits", c["credits"]),
                         "suggested_semester": None, "compulsory": None} for c in courses],
        })
    return {
        "admission_code": "EV2", "name": "Quản lý tài nguyên và môi trường",
        "curriculum_version": "2025", "applies_to_cohorts": ["K70"], "total_credits": 132,
        "source_url": extraction["source_url"], "source_title": "CTĐT EV2 áp dụng từ K70",
        "retrieved_at": "2026-10-27", "graduation_rule": extraction["graduation_formulas"][0]["quote"],
        "groups": groups, "notes": [],
    }


def apply_reviews():
    catalog = load_catalog(DATA / "raw/ctt_course_catalog_all.json")
    manifest = read(DATA / "reviewed/curriculum_resolutions.json")
    approvals_path = DATA / "processed/curriculum_approvals.json"
    approvals = read(approvals_path)
    other_entries = [a for a in approvals["approvals"] if a.get("approved_by") != REVIEWER]
    prepared = []
    for resolution in manifest["resolutions"]:
        source = ROOT / resolution["input_file"]
        if sha(source) != resolution["input_sha256"]:
            raise ValueError(f"Extraction changed; source resolution must be checked again: {source.name}")
        for evidence in resolution["evidence"]:
            if sha(ROOT / evidence["file"]) != evidence["sha256"]:
                raise ValueError(f"Original evidence changed: {evidence['file']}")
        original = read(source)
        raw = convert_ev2(original) if resolution.get("convert") == "ev2" else copy.deepcopy(original)
        raw.update(resolution.get("fields", {}))
        if resolution.get("choice_strategy"):
            merge_choices(raw, resolution["choice_strategy"])
        initial_notes = list(raw.get("notes") or [])
        if resolution.get("fields", {}).get("total_credits"):
            initial_notes = [n for n in initial_notes if not str(n).startswith((
                "Chưa tìm được tổng TC", "Tổng các mức required_credits"))]
        raw["notes"] = initial_notes + resolution["notes"]
        raw["source_review"] = {"reviewed_by": REVIEWER, "evidence": resolution["evidence"],
                                "resolution": resolution["notes"]}
        reviewed_source = DATA / "raw/reviewed_curricula" / f"{resolution['id']}.json"
        write(reviewed_source, raw)
        dataset = build_dataset(raw, reviewed_source.relative_to(ROOT).as_posix(), sha(reviewed_source), catalog,
                                allow_unlisted=True, prefer_source_credits=True)
        dataset["build_warnings"][0] = (
            f"Đã đối chiếu nguồn gốc và quy tắc chọn môn: {raw['source_url']}. "
            "Các môn chưa có trong snapshot CTT vẫn được tính theo tín chỉ CTĐT; chưa xác nhận điều kiện đăng ký."
        )
        dataset["build_warnings"].extend(resolution["notes"])
        for i, evidence in enumerate(resolution["evidence"]):
            dataset["sources"].append({
                "id": f"review_evidence_{i}", "kind": "OFFICIAL_SOURCE_REVIEW",
                "file": evidence["file"], "sha256": evidence["sha256"],
                "authority": "Đại học Bách khoa Hà Nội / đơn vị quản lý chương trình",
                "contains_personal_data": False, "personal_data_included_in_output": False,
            })
        errors, _ = validate_curriculum(dataset, ROOT)
        if errors:
            raise ValueError(f"{resolution['id']}: {errors}")
        target = DATA / "processed/curricula" / output_name(dataset)
        existing = next((a for a in other_entries if a["output_file"] == target.relative_to(ROOT).as_posix()), None)
        if existing:
            raise ValueError(f"Refusing to overwrite another owner's dataset: {target.name}")
        prepared.append((target, dataset, resolution))
    new_entries = []
    for target, dataset, resolution in prepared:
        write(target, dataset)
        new_entries.append({
            "candidate_id": resolution["id"], "source_candidate_id": resolution["source_candidate_id"],
            "status": "approved", "approved_by": REVIEWER,
            "output_file": target.relative_to(ROOT).as_posix(), "notes": resolution["notes"],
        })
        print(f"{resolution['id']}: {len(dataset['courses'])} học phần; {dataset['program']['total_required_credits']} TC")
    approvals["approvals"] = other_entries + new_entries
    write(approvals_path, approvals)


if __name__ == "__main__":
    apply_reviews()
