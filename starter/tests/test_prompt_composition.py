"""The shared question is user input; the selected file is system guidance."""

from __future__ import annotations

import io
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

import main


PROJECT_DIR = Path(main.__file__).resolve().parent


@pytest.mark.parametrize("filename,stage", main.PROMPT_LOOPS.items())
def test_prompt_file_selects_loop_and_combines_prompts(filename, stage, tmp_path):
    prompt_file = PROJECT_DIR / "prompts" / filename
    master = main.read_prompt_file(PROJECT_DIR / "prompts/master_prompt.txt")
    loop_instructions = main.read_prompt_file(prompt_file)
    config = SimpleNamespace(
        output_dir=tmp_path / "outputs",
        inventory_file=tmp_path / "inventory.csv",
        history_file=tmp_path / "history.csv",
        sales_reviews_file=tmp_path / "sales.csv",
        skills_dir=tmp_path / "skills",
    )
    skills = SimpleNamespace(discover=lambda: {})
    with (
        patch.object(sys, "argv", ["main.py", "--prompt-file", str(prompt_file)]),
        patch.object(main.AppConfig, "from_environment", return_value=config),
        patch.object(main, "create_llm_client", return_value=(object(), "test", "mock://")),
        patch.object(main, "SkillCatalog", return_value=skills),
        patch.object(main, "ToolHandlers", return_value=SimpleNamespace(dispatch={})),
        patch.object(main, "ToolRegistry", return_value=SimpleNamespace(definitions=[])),
        patch.object(main, "run_harness") as run_harness,
        redirect_stdout(io.StringIO()),
    ):
        main.main()

    loop, _, user_prompt = run_harness.call_args.args[:3]
    assert isinstance(loop, main.LOOP_STAGES[stage][1])
    assert user_prompt == master
    assert loop_instructions in loop.instructions()
    assert master not in loop.instructions()
    assert run_harness.call_args.args[4] == tmp_path / "outputs" / stage / "prompt/answer.md"


def test_no_prompt_defaults_to_interactive_non_production(tmp_path):
    config = SimpleNamespace(
        output_dir=tmp_path / "outputs",
        inventory_file=tmp_path / "inventory.csv",
        history_file=tmp_path / "history.csv",
        sales_reviews_file=tmp_path / "sales.csv",
        skills_dir=tmp_path / "skills",
    )
    with (
        patch.object(sys, "argv", ["main.py"]),
        patch.object(main.AppConfig, "from_environment", return_value=config),
        patch.object(main, "create_llm_client", return_value=(object(), "test", "mock://")),
        patch.object(main, "SkillCatalog", return_value=SimpleNamespace(discover=lambda: {})),
        patch.object(main, "ToolHandlers", return_value=SimpleNamespace(dispatch={})),
        patch.object(main, "ToolRegistry", return_value=SimpleNamespace(definitions=[])),
        patch("builtins.input", return_value="quit"),
        redirect_stdout(io.StringIO()) as output,
    ):
        main.main()
    assert "Loop stage: non-production" in output.getvalue()


@pytest.mark.parametrize("arguments", [
    ["--loop", "hooks"],
    ["--prompt-file", "prompts/master_prompt.txt"],
    ["--prompt-file", "prompts/unknown.txt"],
])
def test_old_or_unknown_selection_is_rejected(arguments):
    with (
        patch.object(sys, "argv", ["main.py", *arguments]),
        patch.object(main.AppConfig, "from_environment",
                     return_value=SimpleNamespace(output_dir=Path("unused"))),
        redirect_stderr(io.StringIO()),
        pytest.raises(SystemExit) as error,
    ):
        main.main()
    assert error.value.code == 2
