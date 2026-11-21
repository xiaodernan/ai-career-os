"""The author card names the project the one way it is spelled (Epic 368).

Brief X is explicit that a previous pass got this wrong: "项目名称叫'隐盾'，不是'隐图'，
不要写错". A name that appears in a portfolio is the first thing a reader sees and the last
thing they forget, so the card is generated from constants rather than typed prose, and this
gate walks the generated file and the generator itself for the wrong spelling.

It also holds the personal facts to the values that were stated, because the same brief says
the earlier failure was a hallucination: no derived employer, no guessed score, and the two
schools named with the majors they were given with.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GENERATOR = ROOT / "scripts" / "author-card-sync.py"
CARD = ROOT / "frontend" / "public" / "author.html"

# The wrong spelling, named so a reader of this file knows what is being kept out.
WRONG_NAME = "隐图"
RIGHT_NAME = "隐盾"

FACTS = [
    "赵欣曈",
    "南方科技大学",
    "香港中文大学",
    "计算机科学与技术",
    "法狗狗",
    "IELTS 6.5",
    "CET-6 546",
    "全国中学生物理竞赛",
    "江西省一等奖",
]


def test_the_generated_card_names_the_project_correctly() -> None:
    assert CARD.exists(), "the author card was never generated; run scripts/author-card-sync.py"
    text = CARD.read_text(encoding="utf-8")
    assert RIGHT_NAME in text, "the card stopped naming the project at all"
    assert WRONG_NAME not in text, (
        f"the author card spells the project {WRONG_NAME}; brief X names that as the exact "
        "mistake a previous pass made"
    )


def test_the_generator_itself_cannot_spell_the_project_wrong() -> None:
    source = GENERATOR.read_text(encoding="utf-8")
    assert WRONG_NAME not in source, (
        f"the generator carries {WRONG_NAME} anywhere; even in a comment it is one edit away "
        "from the card"
    )
    assert 'PROJECT = "隐盾"' in source, "the project name is no longer a single constant"


def test_the_card_carries_every_fact_that_was_stated() -> None:
    text = CARD.read_text(encoding="utf-8")
    for fact in FACTS:
        assert fact in text, f"the card lost {fact}; brief X says these were hallucinated once"


def test_the_card_is_self_contained_enough_to_embed() -> None:
    """One file, no fetch, no script: an iframe that renders on any origin."""
    text = CARD.read_text(encoding="utf-8")
    assert "<script" not in text, "the card grew a script; a portfolio iframe should not run one"
    assert "http://" not in text.replace("https://", ""), (
        "the card reaches over plain http; an https portfolio would block it"
    )
    assert "github.com/xiaodernan" in text, "the card lost its way back to the author"
