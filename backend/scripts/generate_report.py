#!/usr/bin/env python3
"""
Automated Daily Report Generator

Parses the last 24 hours of telemetry logs and generates a markdown report
with token usage, error counts, and processing statistics.
"""

import json
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path


def get_telemetry_dirs(base_dir: Path | None = None) -> dict[str, Path]:
    """Get telemetry directories."""
    if base_dir is None:
        base_dir = Path(__file__).parent.parent.parent / "data" / "telemetry"

    return {
        "base": base_dir,
        "app": base_dir / "app",
        "ai_traces": base_dir / "ai_traces",
        "reports": base_dir / "reports",
    }


def parse_jsonl_file(file_path: Path, cutoff_time: datetime) -> list[dict]:
    """Parse JSONL file and return entries from last 24 hours."""
    entries = []
    try:
        with open(file_path, "r") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    entry_time = datetime.fromisoformat(
                        entry.get("timestamp", "").replace("Z", "+00:00")
                    )
                    if entry_time >= cutoff_time:
                        entries.append(entry)
                except (json.JSONDecodeError, ValueError):
                    continue
    except FileNotFoundError:
        pass
    return entries


def aggregate_metrics(entries: list[dict]) -> dict:
    """Aggregate metrics from log entries."""
    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_tokens = 0
    error_counts = Counter()
    processing_success = 0

    for entry in entries:
        if "token_usage" in entry:
            tu = entry["token_usage"]
            total_prompt_tokens += tu.get("prompt_tokens", 0)
            total_completion_tokens += tu.get("completion_tokens", 0)
            total_tokens += tu.get("total_tokens", 0)

        level = entry.get("level", "")
        if level in ("ERROR", "CRITICAL"):
            error_type = entry.get("message", "Unknown error")[:100]
            error_counts[error_type] += 1

        if level == "INFO":
            msg = entry.get("message", "")
            if "processed" in msg.lower() or "completed" in msg.lower():
                processing_success += 1

    return {
        "total_prompt_tokens": total_prompt_tokens,
        "total_completion_tokens": total_completion_tokens,
        "total_tokens": total_tokens,
        "error_counts": error_counts,
        "processing_success": processing_success,
    }


def generate_report(output_dir: Path) -> Path:
    """Generate the daily markdown report."""
    dirs = get_telemetry_dirs()

    for dir_path in dirs.values():
        dir_path.mkdir(parents=True, exist_ok=True)

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    now = datetime.now(timezone.utc)
    report_date = now.strftime("%Y_%m_%d")

    all_entries = []

    for log_dir in [dirs["app"], dirs["ai_traces"]]:
        if log_dir.exists():
            for jsonl_file in log_dir.glob("*.jsonl"):
                entries = parse_jsonl_file(jsonl_file, cutoff)
                all_entries.extend(entries)

    metrics = aggregate_metrics(all_entries)

    report_lines = [
        f"# OSINT Platform Daily Report",
        f"",
        f"**Generated:** {now.strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"**Report Period:** Last 24 hours",
        f"",
        f"---",
        f"",
        f"## Summary",
        f"",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total Log Entries | {len(all_entries)} |",
        f"| Documents Processed | {metrics['processing_success']} |",
        f"| Total AI Tokens | {metrics['total_tokens']:,} |",
        f"| Prompt Tokens | {metrics['total_prompt_tokens']:,} |",
        f"| Completion Tokens | {metrics['total_completion_tokens']:,} |",
        f"| Total Errors | {sum(metrics['error_counts'].values())} |",
        f"",
        f"---",
        f"",
        f"## Top Errors",
        f"",
    ]

    if metrics["error_counts"]:
        report_lines.append("| Error Message | Count |")
        report_lines.append("|--------------|-------|")
        for error_msg, count in metrics["error_counts"].most_common(10):
            error_msg_escaped = error_msg.replace("|", "\\|")
            report_lines.append(f"| {error_msg_escaped} | {count} |")
    else:
        report_lines.append("*No errors detected in the last 24 hours.*")

    report_lines.extend(
        [
            "",
            "---",
            "",
            "## AI Model Usage",
            "",
        ]
    )

    model_counts = Counter()
    for entry in all_entries:
        if "model" in entry:
            model_counts[entry["model"]] += 1

    if model_counts:
        report_lines.append("| Model | Requests |")
        report_lines.append("|-------|----------|")
        for model, count in model_counts.most_common():
            report_lines.append(f"| {model} | {count} |")
    else:
        report_lines.append("*No AI requests in the last 24 hours.*")

    report_lines.extend(
        [
            "",
            "---",
            "",
            "## Log Sources",
            "",
            f"- App logs: `{dirs['app']}`",
            f"- AI traces: `{dirs['ai_traces']}`",
            "",
        ]
    )

    report_content = "\n".join(report_lines)
    report_path = output_dir / f"report_{report_date}.md"

    with open(report_path, "w") as f:
        f.write(report_content)

    return report_path


if __name__ == "__main__":
    dirs = get_telemetry_dirs()
    report_path = generate_report(dirs["reports"])
    print(f"Report generated: {report_path}")
