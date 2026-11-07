"""Run offline assistant/router evaluation prompts.

Default mode uses the reusable NLU classifier so this suite can run without
starting FastAPI or calling network providers. It writes JSON and Markdown
reports under backend/evals/results/.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.nlu.classifier import classify  # noqa: E402


DEFAULT_EVAL_PATH = BACKEND_DIR / "evals" / "prompts_assistant_quality.jsonl"
RESULTS_DIR = BACKEND_DIR / "evals" / "results"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            clean = line.strip()
            if not clean:
                continue
            try:
                records.append(json.loads(clean))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_no}: {exc}") from exc
    return records


def observed_text(result: Any) -> str:
    data = asdict(result)
    active_flags = [key for key in ("needs_tool", "needs_search", "needs_llm", "needs_action", "needs_clarification") if data.get(key)]
    parts = [
        str(data.get("intent", "")),
        str(data.get("route", "")),
        str(data.get("language_style", "")),
        str(data.get("normalized_text", "")),
        str(data.get("reason", "")),
        json.dumps(data.get("entities", {}), ensure_ascii=False),
        " ".join(active_flags),
    ]
    return " ".join(parts).lower()


def run_record(record: dict[str, Any]) -> dict[str, Any]:
    result = classify(record["input"])
    text = observed_text(result)
    failures: list[str] = []

    if result.intent != record["expected_intent"]:
        failures.append(f"intent expected {record['expected_intent']} got {result.intent}")
    if result.route != record["expected_route"]:
        failures.append(f"route expected {record['expected_route']} got {result.route}")
    for term in record.get("must_include", []):
        if str(term).lower() not in text:
            failures.append(f"missing required term: {term}")
    for term in record.get("must_not_include", []):
        if str(term).lower() in text:
            failures.append(f"forbidden term present: {term}")
    if record.get("safety") == "blocked" and result.route != "blocked":
        failures.append("safety expected blocked route")
    if record.get("safety") == "draft_only" and "auto_send" in text:
        failures.append("draft_only record exposed auto_send")

    return {
        "id": record["id"],
        "input": record["input"],
        "expected_intent": record["expected_intent"],
        "actual_intent": result.intent,
        "expected_route": record["expected_route"],
        "actual_route": result.route,
        "safety": record.get("safety", "safe"),
        "passed": not failures,
        "failures": failures,
        "observed": asdict(result),
    }


def write_reports(results: list[dict[str, Any]], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"assistant_eval_report_{timestamp}.json"
    md_path = output_dir / f"assistant_eval_report_{timestamp}.md"
    total = len(results)
    passed = sum(1 for item in results if item["passed"])
    pass_rate = round((passed / total) * 100, 2) if total else 0.0

    json_path.write_text(
        json.dumps(
            {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "total": total,
                "passed": passed,
                "failed": total - passed,
                "pass_rate": pass_rate,
                "results": results,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    lines = [
        "# Assistant Eval Report",
        "",
        f"- Total: {total}",
        f"- Passed: {passed}",
        f"- Failed: {total - passed}",
        f"- Pass rate: {pass_rate}%",
        "",
        "| ID | Input | Expected | Actual | Result |",
        "|---|---|---|---|---|",
    ]
    for item in results:
        result = "PASS" if item["passed"] else "FAIL: " + "; ".join(item["failures"])
        lines.append(
            f"| {item['id']} | {item['input']} | {item['expected_intent']} / {item['expected_route']} | "
            f"{item['actual_intent']} / {item['actual_route']} | {result} |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Nexa assistant eval prompts.")
    parser.add_argument("--eval-file", default=str(DEFAULT_EVAL_PATH), help="JSONL eval file path")
    parser.add_argument("--output-dir", default=str(RESULTS_DIR), help="Directory for JSON/Markdown reports")
    args = parser.parse_args()

    records = load_jsonl(Path(args.eval_file))
    results = [run_record(record) for record in records]
    json_path, md_path = write_reports(results, Path(args.output_dir))
    total = len(results)
    passed = sum(1 for item in results if item["passed"])
    pass_rate = round((passed / total) * 100, 2) if total else 0.0

    print(f"Assistant evals: {passed}/{total} passed ({pass_rate}%)")
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {md_path}")
    if passed != total:
        print("\nFailures:")
        for item in results:
            if not item["passed"]:
                print(f"- {item['id']}: {'; '.join(item['failures'])}")
    return 0 if pass_rate >= 95.0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
