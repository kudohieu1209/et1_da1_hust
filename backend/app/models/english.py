from typing import Literal

from pydantic import BaseModel, Field


class SourceEvidence(BaseModel):
    source: str
    quote: str


class EnglishResult(BaseModel):
    score: float | None = None
    listening: float | None = None
    reading: float | None = None
    speaking: float | None = None
    writing: float | None = None
    test_date: str | None = None
    certificate_type: str | None = None


class ConversionRow(SourceEvidence):
    level: str
    placement: tuple[int, int] | None
    skills: tuple[tuple[int, int], ...] | None
    note: str | None = None


class GraduationRequirement(SourceEvidence):
    level: int | None
    note: str | None = None


class RegistrationRequirement(SourceEvidence):
    semesters: list[int]
    placement_table: str | None
    courses: list[str]


class EnglishRule(SourceEvidence):
    decision: str
    applies_from_cohort: int
    applies_to_cohort: int | None
    source_file: str
    conversion_table: list[ConversionRow]
    graduation: dict[str, GraduationRequirement]
    registration_by_semester: dict[str, list[RegistrationRequirement]]


class EnglishRequirements(BaseModel):
    graduation: GraduationRequirement
    registration_by_semester: list[RegistrationRequirement]


class EnglishStandardResponse(BaseModel):
    cohort: int | None = None
    track: Literal["standard", "talent", "elitech", "unknown"] = "unknown"
    ctt_status: Literal["completed", "incomplete", "unverified"] = "unverified"
    latest: EnglishResult | None = None
    estimated_level: str | None = None
    rule: EnglishRule | None = None
    required: EnglishRequirements | None = None
    history: list[EnglishResult] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    has_data: bool = False
