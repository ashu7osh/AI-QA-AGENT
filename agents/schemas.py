"""
Shared data models for the AI QA Agent pipeline.
Every agent (planner, generator, analyzer) passes data around using these
typed models instead of raw dicts/strings, so the pipeline stays predictable
even though an LLM is generating parts of the content.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class TestStep(BaseModel):
    """One human-readable step in a test plan (not code yet)."""
    step_number: int
    action: str = Field(..., description="What to do, e.g. 'Fill username field'")
    target: Optional[str] = Field(None, description="Element/selector hint, e.g. '#username'")
    value: Optional[str] = Field(None, description="Value to type/select, if any")
    expected_result: Optional[str] = Field(None, description="What should happen after this step")


class TestPlan(BaseModel):
    """Output of the Planner Agent."""
    title: str
    url: str
    steps: List[TestStep]
    assertions: List[str] = Field(default_factory=list, description="High-level pass/fail checks")


class GeneratedTest(BaseModel):
    """Output of the Test Generator Agent."""
    plan_title: str
    code: str = Field(..., description="Full, runnable Playwright Python function body")
    filename: str


class ExecutionResult(BaseModel):
    """Output of the Playwright Executor."""
    test_title: str
    passed: bool
    duration_seconds: float
    console_logs: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None
    error_traceback: Optional[str] = None
    screenshot_path: Optional[str] = None
    trace_path: Optional[str] = None
    video_path: Optional[str] = None


class BugReport(BaseModel):
    """Output of the Bug Analysis Agent (only produced on failure)."""
    bug_title: str
    severity: str  # Low / Medium / High / Critical
    expected: str
    actual: str
    possible_root_cause: str
    suggested_fix: str
    evidence_screenshot: Optional[str] = None
