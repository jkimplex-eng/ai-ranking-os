import html
import json
from pathlib import Path
from typing import Any


def _status_class(status: str) -> str:
    return "pass" if status == "PASS" else "fail"


def render_html(report: dict[str, Any]) -> str:
    check_rows_list = []
    for check in report["checks"]:
        details = html.escape(
            json.dumps(check["details"], ensure_ascii=False, indent=2)
        )
        check_rows_list.append(
            "<tr>"
            f"<td>{html.escape(check['name'])}</td>"
            f"<td class='{_status_class(check['status'])}'>{check['status']}</td>"
            f"<td><pre>{details}</pre></td>"
            "</tr>"
        )
    check_rows = "\n".join(check_rows_list)
    matrix_rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(row['producer'])}</td>"
        f"<td>{html.escape(row['consumer'])}</td>"
        f"<td>{html.escape(row['contract'])}</td>"
        f"<td class='{_status_class(row['status'])}'>{row['status']}</td>"
        "</tr>"
        for row in report["compatibility_matrix"]
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>AI Ranking OS Pipeline Validation</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #172033; }}
    table {{ border-collapse: collapse; width: 100%; margin-bottom: 2rem; }}
    th, td {{ border: 1px solid #d9deea; padding: .6rem; text-align: left; }}
    th {{ background: #f3f5fa; }} .pass {{ color: #08783e; font-weight: 700; }}
    .fail {{ color: #b42318; font-weight: 700; }} pre {{ white-space: pre-wrap; }}
  </style>
</head>
<body>
  <h1>AI Ranking OS Pipeline Validation</h1>
  <p>Overall: <strong class="{_status_class(report['status'])}">{report['status']}</strong></p>
  <p>Correlation ID: <code>{html.escape(report['correlation_id'])}</code></p>
  <h2>Checks</h2>
  <table><thead><tr><th>Check</th><th>Status</th><th>Details</th></tr></thead>
  <tbody>{check_rows}</tbody></table>
  <h2>Compatibility Matrix</h2>
  <table><thead><tr><th>Producer</th><th>Consumer</th><th>Contract</th><th>Status</th></tr></thead>
  <tbody>{matrix_rows}</tbody></table>
  <h2>Coverage</h2><pre>{html.escape(json.dumps(report['coverage'], indent=2))}</pre>
  <h2>Performance</h2><pre>{html.escape(json.dumps(report['performance'], indent=2))}</pre>
</body>
</html>
"""


def write_reports(report: dict[str, Any], output_directory: str | Path) -> dict[str, str]:
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    paths = {
        "json_report": output / "pipeline-validation.json",
        "html_report": output / "pipeline-validation.html",
        "coverage_report": output / "coverage-report.json",
        "compatibility_matrix": output / "compatibility-matrix.json",
    }
    paths["json_report"].write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    paths["html_report"].write_text(render_html(report), encoding="utf-8")
    paths["coverage_report"].write_text(
        json.dumps(report["coverage"], indent=2),
        encoding="utf-8",
    )
    paths["compatibility_matrix"].write_text(
        json.dumps(report["compatibility_matrix"], indent=2),
        encoding="utf-8",
    )
    return {name: str(path.resolve()) for name, path in paths.items()}
