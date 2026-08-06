"""
AI QA Agent - Orchestrator
--------------------------
Entry point. Wires the pipeline together:

    User instruction
        -> Planner Agent      (plain English -> structured TestPlan)
        -> Generator Agent    (TestPlan -> Playwright code)
        -> Executor           (runs the code in a real browser)
        -> Analyzer Agent     (only if it failed -> BugReport)
        -> Report Builder     (HTML report with everything)

This file is intentionally written as a plain linear pipeline (not LangGraph)
so you can get a working demo fast. Each step is already a pure function
taking/returning a Pydantic model, which is exactly what LangGraph nodes look
like — see the "Upgrading to LangGraph" note at the bottom of this file for
how to port it in ~30 minutes once the linear version works end-to-end.

Usage:
    python app.py "Test login using invalid credentials" --url https://www.saucedemo.com
"""

import argparse
import sys
from rich import print as rprint

from agents.planner import plan_test
from agents.generator import generate_test
from executor.runner import run_generated_test_with_retry
from agents.analyzer import analyze_failure
from reports.report_builder import build_report


def run_pipeline_steps(instruction: str, base_url: str, headless: bool = True):
    """Runs the full pipeline and returns every intermediate object
    (plan, generated test, execution result, bug report, report path).

    This is the function both the CLI (`main()` below) and the pytest
    wrapper (tests/test_ai_pipeline.py) call, so there is exactly one
    implementation of the pipeline, not a CLI copy and a test copy."""
    rprint(f"[bold cyan]1. Planning test for:[/bold cyan] {instruction}")
    plan = plan_test(instruction, base_url)
    rprint(f"   -> Plan created: [bold]{plan.title}[/bold] ({len(plan.steps)} steps)")

    rprint("[bold cyan]2. Generating Playwright code...[/bold cyan]")
    generated = generate_test(plan)
    rprint(f"   -> Code generated: {generated.filename}")

    rprint("[bold cyan]3. Executing in browser...[/bold cyan]")
    result = run_generated_test_with_retry(generated, headless=headless, max_attempts=2)
    status = "[bold green]PASSED[/bold green]" if result.passed else "[bold red]FAILED[/bold red]"
    rprint(f"   -> Result: {status} in {result.duration_seconds}s")

    bug_report = None
    if not result.passed:
        rprint("[bold cyan]4. Analyzing failure...[/bold cyan]")
        bug_report = analyze_failure(plan, result)
        rprint(f"   -> Bug: [bold]{bug_report.bug_title}[/bold] (Severity: {bug_report.severity})")

    rprint("[bold cyan]5. Building report...[/bold cyan]")
    report_path = build_report(result, generated, bug_report)
    rprint(f"[bold green]Done! Report saved to:[/bold green] {report_path}")

    return plan, generated, result, bug_report, report_path


def run_pipeline(instruction: str, base_url: str, headless: bool = True) -> str:
    """Backwards-compatible CLI entry point - just returns the report path."""
    _, _, _, _, report_path = run_pipeline_steps(instruction, base_url, headless)
    return report_path


def main():
    parser = argparse.ArgumentParser(description="AI QA Agent - Agentic Playwright Testing Assistant")
    parser.add_argument("instruction", help='Plain English instruction, e.g. "Test login using invalid credentials"')
    parser.add_argument("--url", default="https://www.saucedemo.com", help="Base URL to test")
    parser.add_argument("--headed", action="store_true", help="Run browser with a visible window (default: headless)")
    args = parser.parse_args()

    try:
        run_pipeline(args.instruction, args.url, headless=not args.headed)
    except Exception as e:
        rprint(f"[bold red]Pipeline error:[/bold red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

"""
Upgrading to LangGraph (later, optional)
-----------------------------------------
Each function above (plan_test, generate_test, run_generated_test,
analyze_failure, build_report) already takes typed input and returns typed
output — that's exactly what a LangGraph node function looks like. To port:

1. pip install langgraph
2. Define a TypedDict/Pydantic `GraphState` holding: instruction, base_url,
   plan, generated_test, result, bug_report, report_path.
3. Wrap each function as a node: `def planner_node(state): state["plan"] =
   plan_test(state["instruction"], state["base_url"]); return state`
4. Build the graph:
     graph = StateGraph(GraphState)
     graph.add_node("planner", planner_node)
     graph.add_node("generator", generator_node)
     graph.add_node("executor", executor_node)
     graph.add_conditional_edges("executor", lambda s: "analyzer" if not s["result"].passed else "reporter")
     graph.add_node("analyzer", analyzer_node)
     graph.add_node("reporter", reporter_node)
     graph.set_entry_point("planner")
     graph.add_edge("planner", "generator")
     graph.add_edge("generator", "executor")
     graph.add_edge("analyzer", "reporter")
     app = graph.compile()
5. Run with app.invoke({...initial state...})

This gets you the "LangGraph" resume bullet with minimal rework, once the
core logic is already proven to work.
"""
