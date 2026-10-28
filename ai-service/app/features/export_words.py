"""The words of the export's readable half, in every language it ships in.

The export has two faces: the JSON a machine reads and the document a person
reads -- the Markdown view and the print-ready HTML. The document was
written in Chinese and had no other language, so an English reader's
"printable document" was a Chinese document: the section names, the title,
the headings, the labels, all of it. That is the same class of defect as
the rest of the i18n holes -- a word the reader cannot change -- except that
here the words are not on a screen at all, so the copy census cannot see
them either: they live in a server-side module, in a document.

So the words live in one table, in one place, and the render reads the
table for the language it is asked for. The keys are the bundle's own
section names, so the table and the bundle cannot drift apart without the
gate that holds them together saying so.

The default is English, which is the default everywhere else in this
product; the caller says which language it wants.
"""

from __future__ import annotations

from typing import Any

# The languages the readable half ships in.
LOCALES: tuple[str, ...] = ("en", "zh")

# The section names, in display order, per language.
_SECTIONS: dict[str, dict[str, str]] = {
    "en": {
        "profile": "Profile",
        "resumes": "Resumes",
        "knowledge": "Knowledge base",
        "job_descriptions": "Job descriptions",
        "interviews": "Mock interviews",
        "memories": "Long-term memories",
        # The two the BACKEND owns (1.1.0) -- the pipeline the candidate worked
        # and the growth runs they built. A readable export that left them out
        # would be a reading list, not a record of the search.
        "applications": "Applications",
        "growth_plans": "Growth runs",
        # And the two the reader typed into (1.2.0).
        "notes": "Notes",
        "contacts": "Contacts",
    },
    "zh": {
        "profile": "个人档案",
        "resumes": "简历版本",
        "knowledge": "知识库",
        "job_descriptions": "职位描述",
        "interviews": "模拟面试",
        "memories": "长期记忆",
        "applications": "申请记录",
        "growth_plans": "成长报告",
        "notes": "笔记",
        "contacts": "联系人",
    },
}

# The document's own words.
_WORDS: dict[str, dict[str, str]] = {
    "en": {
        "title": "AI Career OS — Data export",
        "generated": "Generated",
        "anonymous": "⚠ Anonymized export (identifying fields removed)",
        "userId": "User ID",
        "anonymized": "(anonymized)",
        "schema": "Schema",
        "contentHash": "Content hash",
        "stats": "Statistics",
        "interview": "Interview",
        "rounds": "rounds",
        "coverage": "coverage",
    },
    "zh": {
        "title": "AI Career OS — 数据导出",
        "generated": "生成时间",
        "anonymous": "⚠ 已匿名导出（个人标识字段已移除）",
        "userId": "用户 ID",
        "anonymized": "（已匿名）",
        "schema": "Schema",
        "contentHash": "内容哈希",
        "stats": "统计",
        "interview": "面试",
        "rounds": "轮",
        "coverage": "覆盖率",
    },
}

# The order the sections are rendered in.
SECTION_ORDER: tuple[str, ...] = (
    "profile",
    "resumes",
    "knowledge",
    "job_descriptions",
    "interviews",
    "memories",
    "applications",
    "growth_plans",
    "notes",
    "contacts",
)

# The headings of the single-version print view (19.5). Same rule as the
# bundle's section names: the document is the reader's, so the words come from
# a table rather than from the resume body -- a Chinese reader's printable
# resume must not carry English headings because the tailoring prompt wrote
# them that way.
_RESUME_SECTIONS: dict[str, dict[str, str]] = {
    "en": {
        "summary": "Summary",
        "experience": "Experience",
        "projects": "Projects",
        "education": "Education",
        "skills": "Skills",
        "achievements": "Achievements",
        "gpa": "GPA",
    },
    "zh": {
        "summary": "摘要",
        "experience": "工作经历",
        "projects": "项目经历",
        "education": "教育背景",
        "skills": "技能",
        "achievements": "成就",
        "gpa": "GPA",
    },
}


def normalize_locale(locale: Any) -> str:
    """The language to render in, from whatever the caller had.

    An unknown language is English rather than a guess: the table is the
    product's account of itself, and a language it does not have is one it
    must not pretend to.
    """
    if isinstance(locale, str):
        head = locale.split("-")[0].strip().lower()
        if head in LOCALES:
            return head
    return "en"


def words(locale: Any = None) -> dict[str, str]:
    """The document's own words, in the language asked for."""
    return _WORDS[normalize_locale(locale)]


def section_titles(locale: Any = None) -> dict[str, str]:
    """The section names, in the language asked for."""
    return _SECTIONS[normalize_locale(locale)]


def resume_titles(locale: Any = None) -> dict[str, str]:
    """The single-version print view's headings, in the language asked for."""
    return _RESUME_SECTIONS[normalize_locale(locale)]
