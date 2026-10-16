from __future__ import annotations

from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / ".harness"

REQUIRED_FILES = [
    ".harness/README.md",
    ".harness/implementation-plan.md",
    ".harness/domains/store-diagnosis-baseline.md",
    ".harness/rules/00-index.md",
    ".harness/rules/01-agent-collaboration.md",
    ".harness/rules/02-git-worktree.md",
    ".harness/rules/03-testing-tdd.md",
    ".harness/rules/04-quality-gates.md",
    ".harness/rules/05-openspec-lifecycle.md",
    ".harness/rules/06-module-boundaries.md",
    ".harness/skills/request-analysis/SKILL.md",
    ".harness/skills/solution-design-task-breakdown/SKILL.md",
    ".harness/skills/tdd-implementation/SKILL.md",
    ".harness/skills/verification/SKILL.md",
    ".harness/skills/worktree-development/SKILL.md",
    ".harness/skills/uat-deploy/SKILL.md",
]

SKILL_PATTERN = re.compile(r"^---\nname: [a-z0-9-]+\ndescription: .+\n---\n", re.MULTILINE)
MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)#]+?)(?:#[^)]*)?\)")


def main() -> int:
    errors: list[str] = []
    for relative in REQUIRED_FILES:
        if not (ROOT / relative).is_file():
            errors.append(f"missing required file: {relative}")

    markdown_files = list((HARNESS / "rules").glob("*.md"))
    markdown_files.extend((HARNESS / "skills").glob("*/SKILL.md"))
    markdown_files.extend([HARNESS / "README.md", HARNESS / "implementation-plan.md", HARNESS / "domains/store-diagnosis-baseline.md"])

    for path in markdown_files:
        relative = path.relative_to(ROOT).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(f"not UTF-8: {relative}")
            continue

        for match in MARKDOWN_LINK_PATTERN.finditer(text):
            target = match.group(1)
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            target_path = (path.parent / target).resolve()
            if not target_path.exists():
                errors.append(f"broken link in {relative}: {target}")

    for path in (HARNESS / "skills").glob("*/SKILL.md"):
        relative = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        if not SKILL_PATTERN.match(text):
            errors.append(f"invalid frontmatter: {relative}")

    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    if ".harness/rules/00-index.md" not in agents:
        errors.append("AGENTS.md does not reference .harness/rules/00-index.md")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"Harness structure verified: {len(REQUIRED_FILES)} required files present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
