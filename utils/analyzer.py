import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Issue:
    name: str
    severity: str
    line_ref: str
    explanation: str
    fix: str
    category: str


@dataclass
class ReviewResult:
    issues: list[Issue] = field(default_factory=list)
    security_score: int = 0
    logic_score: int = 0
    scale_score: int = 0
    quality_score: int = 0
    overall_score: int = 0
    verdict: str = ""
    raw_output: str = ""
    error: Optional[str] = None

    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "CRITICAL")

    @property
    def high_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "HIGH")

    @property
    def medium_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "MEDIUM")

    @property
    def low_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "LOW")

    @property
    def is_safe_to_ship(self) -> bool:
        return self.critical_count == 0 and self.high_count == 0

    @property
    def overall_label(self) -> str:
        if self.overall_score >= 90:
            return "Excellent"
        elif self.overall_score >= 75:
            return "Good"
        elif self.overall_score >= 60:
            return "Needs Work"
        elif self.overall_score >= 40:
            return "Risky"
        else:
            return "Do Not Ship"


def parse_full_review(raw_output: str) -> ReviewResult:
    result = ReviewResult(raw_output=raw_output)

    try:
        result.security_score = _extract_score(raw_output, "SECURITY SCORE")
        result.logic_score     = _extract_score(raw_output, "LOGIC SCORE")
        result.scale_score     = _extract_score(raw_output, "SCALE SCORE")
        result.quality_score   = _extract_score(raw_output, "QUALITY SCORE")
        result.overall_score   = _extract_score(raw_output, "OVERALL SCORE")

        scores = [result.security_score, result.logic_score,
                  result.scale_score, result.quality_score]
        valid = [s for s in scores if s > 0]
        if result.overall_score == 0 and valid:
            result.overall_score = int(
                (result.security_score * 2 + result.logic_score +
                 result.scale_score + result.quality_score) / 5
            )

        verdict_match = re.search(
            r"== VERDICT ==\s*(.*?)(?:\Z|==)",
            raw_output, re.DOTALL | re.IGNORECASE
        )
        if verdict_match:
            result.verdict = verdict_match.group(1).strip()

        sections = {
            "security":    re.search(r"== SECURITY ==(.*?)(?:== LOGIC|== SCALABILITY|== CODE QUALITY|== SCORES|$)", raw_output, re.DOTALL | re.IGNORECASE),
            "logic":       re.search(r"== LOGIC ==(.*?)(?:== SCALABILITY|== CODE QUALITY|== SCORES|$)", raw_output, re.DOTALL | re.IGNORECASE),
            "scalability": re.search(r"== SCALABILITY ==(.*?)(?:== CODE QUALITY|== SCORES|$)", raw_output, re.DOTALL | re.IGNORECASE),
            "quality":     re.search(r"== CODE QUALITY ==(.*?)(?:== SCORES|$)", raw_output, re.DOTALL | re.IGNORECASE),
        }

        for category, match in sections.items():
            if match:
                section_text = match.group(1)
                issues = _parse_issues_from_section(section_text, category)
                result.issues.extend(issues)

    except Exception as e:
        result.error = f"Parse error (showing raw output): {str(e)}"

    return result


def _extract_score(text: str, label: str) -> int:
    pattern = rf"{re.escape(label)}:\s*(\d+)"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        score = int(match.group(1))
        return max(0, min(100, score))
    return 0


def _parse_issues_from_section(section_text: str, category: str) -> list[Issue]:
    issues = []

    pipe_pattern = re.compile(
        r"(?:^|\n)\s*(.*?)\s*\|\s*(CRITICAL|HIGH|MEDIUM|LOW)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)(?=\n\S|\Z)",
        re.IGNORECASE | re.DOTALL
    )
    for match in pipe_pattern.finditer(section_text):
        name, severity, line_ref, explanation, fix = match.groups()
        if name.strip() and "no issues" not in name.lower():
            issues.append(Issue(
                name=name.strip(),
                severity=severity.upper(),
                line_ref=line_ref.strip(),
                explanation=explanation.strip(),
                fix=fix.strip(),
                category=category
            ))

    if not issues:
        blocks = re.split(r"\n(?=ISSUE:)", section_text, flags=re.IGNORECASE)
        for block in blocks:
            if not block.strip() or "no issues" in block.lower():
                continue
            name        = _extract_field(block, "ISSUE")
            severity    = _extract_field(block, "SEVERITY").upper()
            line_ref    = _extract_field(block, "LINE REFERENCE|LINE REF|LINE")
            explanation = _extract_field(block, "EXPLANATION")
            fix         = _extract_field(block, "FIX")

            if name and severity in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
                issues.append(Issue(
                    name=name,
                    severity=severity,
                    line_ref=line_ref,
                    explanation=explanation,
                    fix=fix,
                    category=category
                ))

    return issues


def _extract_field(text: str, label_pattern: str) -> str:
    pattern = rf"(?:{label_pattern}):\s*(.*?)(?:\n[A-Z]|\Z)"
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""