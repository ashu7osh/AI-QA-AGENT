
"""Build the HTML report for an AI QA Agent execution."""

import os
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from jinja2 import Environment, FileSystemLoader

from agents.schemas import ExecutionResult, BugReport, GeneratedTest

TEMPLATE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = TEMPLATE_DIR
PROJECT_ROOT = TEMPLATE_DIR.parent


def _resolve_artifact_path(artifact_path, report_dir: Path) -> str | None:
    """Return a relative URL only when the artifact exists."""
    if not artifact_path:
        return None

    path = Path(artifact_path).expanduser()

    candidates = (
        [path]
        if path.is_absolute()
        else [
            PROJECT_ROOT / path,
            Path.cwd() / path,
            report_dir / path,
        ]
    )

    for candidate in candidates:
        if candidate.is_file():
            relative = os.path.relpath(
                candidate.resolve(), report_dir.resolve()
            )
            return quote(Path(relative).as_posix(), safe="/")

    return None


def build_report(
    result: ExecutionResult,
    generated_test: GeneratedTest,
    bug_report: BugReport | None = None,
) -> str:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    safe_name = Path(generated_test.filename).stem
    out_path = OUTPUT_DIR / f"report_{safe_name}.html"

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=True,
    )
    template = env.get_template("report_template.html")

    html = template.render(
        result=result,
        bug_report=bug_report,
        generated_code=generated_test.code,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        screenshot_path=_resolve_artifact_path(
            result.screenshot_path, OUTPUT_DIR
        ),
        trace_path=_resolve_artifact_path(result.trace_path, OUTPUT_DIR),
        video_path=_resolve_artifact_path(result.video_path, OUTPUT_DIR),
    )

    out_path.write_text(html, encoding="utf-8")
    return str(out_path)
