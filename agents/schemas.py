"""
Shared data models for the AI QA Agent pipeline.
Every agent (planner, generator, analyzer) passes data around using these
typed models instead of raw dicts/strings, so the pipeline stays predictable
even though an LLM is generating parts of the content.
"""

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TestStep(StrictSchema):
    step_number: int = Field(ge=1)
    action: str = Field(min_length=1)
    target: str | None = None
    value: str | None = None
    expected_result: str | None = None

    @field_validator("action")
    @classmethod
    def action_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("action must not be blank")
        return value


class TestPlan(StrictSchema):
    __test__ = False
    title: str = Field(min_length=1)
    url: str = Field(min_length=1)
    steps: list[TestStep] = Field(min_length=1)
    assertions: list[str] = Field(default_factory=list)

    @field_validator("title", "url")
    @classmethod
    def required_text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Field must not be blank")
        return value

    @field_validator("assertions")
    @classmethod
    def assertions_must_not_be_blank(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("Assertions must not contain blank strings")
        return values


class GeneratedTest(StrictSchema):
    plan_title: str = Field(min_length=1)
    code: str = Field(min_length=1)
    filename: str = Field(min_length=1)


class ExecutionResult(BaseModel):
    test_title: str
    passed: bool
    duration_seconds: float
    console_logs: list[str] = Field(default_factory=list)
    error_message: str | None = None
    error_traceback: str | None = None
    screenshot_path: str | None = None
    trace_path: str | None = None
    video_path: str | None = None


class BugReport(StrictSchema):
    bug_title: str = Field(min_length=1)
    severity: Literal["Low", "Medium", "High", "Critical"]
    expected: str = Field(min_length=1)
    actual: str = Field(min_length=1)
    possible_root_cause: str = Field(min_length=1)
    suggested_fix: str = Field(min_length=1)
    evidence_screenshot: str | None = None
