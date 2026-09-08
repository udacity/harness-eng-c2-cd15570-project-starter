"""Save completed-run evidence; this module does not provide conversation memory.

The harness writes the final model answer and tool trace to files so they can
be reviewed later. Interactive-session memory instead comes from the Responses
API previous_response_id held in main.py, and it is lost when the program exits.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_run_artifacts(
    response: Any,
    tool_run_log: list[dict[str, Any]],
    output_file: Path,
    tool_log_file: Path,
) -> None:
    for path in (output_file, tool_log_file):
        path.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(response.output_text + "\n", encoding="utf-8")
    tool_log_file.write_text(json.dumps(tool_run_log, indent=2) + "\n", encoding="utf-8")


def write_evaluation_artifact(evaluation: dict[str, Any], evaluation_file: Path) -> None:
    """Save the structured retrospective evaluation for one completed task."""
    evaluation_file.parent.mkdir(parents=True, exist_ok=True)
    evaluation_file.write_text(json.dumps(evaluation, indent=2) + "\n", encoding="utf-8")
