"""Pydantic contracts for AI feature outputs (stored in jsonb, rendered by frontend)."""

from pydantic import BaseModel, Field


class ParsedExperience(BaseModel):
    company: str
    title: str
    start: str = ""
    end: str = ""
    location: str = ""
    bullets: list[str] = Field(default_factory=list)
    summary: str = ""


class ParsedProject(BaseModel):
    name: str
    role: str = ""
    period: str = ""
    bullets: list[str] = Field(default_factory=list)
    tech: list[str] = Field(default_factory=list)
    url: str = ""


class ParsedEducation(BaseModel):
    school: str
    degree: str = ""
    field: str = ""
    startYear: int | None = None
    endYear: int | None = None
    gpa: str = ""
    courses: list[str] = Field(default_factory=list)


class ParsedSkill(BaseModel):
    name: str
    category: str = "other"
    proficiency: float | None = None


class ResumeProfile(BaseModel):
    """Canonical structured resume JSON (PRD §3)."""

    name: str = ""
    headline: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    links: dict[str, str] = Field(default_factory=dict)
    summary: str = ""
    yearsExperience: float | None = None


class ResumeParseResult(BaseModel):
    profile: ResumeProfile = Field(default_factory=ResumeProfile)
    education: list[ParsedEducation] = Field(default_factory=list)
    experience: list[ParsedExperience] = Field(default_factory=list)
    projects: list[ParsedProject] = Field(default_factory=list)
    skills: list[ParsedSkill] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    careerGoals: list[str] = Field(default_factory=list)
    preferredRoles: list[str] = Field(default_factory=list)
    preferredLocations: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    missingSections: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SkillRequirement(BaseModel):
    name: str
    priority: str = "must"      # must | should | nice
    evidence_phrase: str = ""


class JDAnalysis(BaseModel):
    title: str = ""
    company: str = ""
    location: str = ""
    experienceYears: float | None = None
    education: dict = Field(default_factory=dict)
    requiredSkills: list[SkillRequirement] = Field(default_factory=list)
    preferredSkills: list[SkillRequirement] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    softSkills: list[str] = Field(default_factory=list)
    hiddenRequirements: list[str] = Field(default_factory=list)
    interviewTopics: list[str] = Field(default_factory=list)
    priorityOrder: list[str] = Field(default_factory=list)
    domainKeywords: list[str] = Field(default_factory=list)
    resumeImprovementSuggestions: list[str] = Field(default_factory=list)


class EvidenceItem(BaseModel):
    criterion: str
    score: float
    chunk_ids: list[str] = Field(default_factory=list)
    quote: str = ""
    source: str = ""
    section: str = ""
    reasoning: str = ""


class SkillGap(BaseModel):
    skill: str
    importance: str = "must"
    advice: str = ""


class MatchResult(BaseModel):
    overall: float
    technical: float
    experience: float
    projects: float
    education: float
    matchedSkills: list[str] = Field(default_factory=list)
    missingSkills: list[str] = Field(default_factory=list)
    skillGaps: list[SkillGap] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    narrative: str = ""
    interviewTopics: list[str] = Field(default_factory=list)
    model: str = ""
