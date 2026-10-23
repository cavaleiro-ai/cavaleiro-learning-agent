"""The approval floors resume scanning after a heredoc terminator with a clean quote state.

Regression for #140704. The detection lexer had no heredoc model, so a heredoc body was read as
shell. One unbalanced quote in a body ("it's done") opened a quote that never closed, and every
later line was quoted data to the scanner: the hardline floor, ``approvals.deny`` and the
dangerous-pattern detector all missed ``rm -rf /`` on the line after the terminator, so it ran
under ``approvals.mode: off`` / ``--yolo``. Heredoc bodies are data for their consumer and the
shell resumes normal parsing after the terminator; the floors now do too, while still scanning
the bodies themselves (``bash <<EOF`` executes its body).
"""
import pytest

from tools import approval as mod
from tools import approval_context
from tools.approval_detection import detect_dangerous_command, detect_hardline_command

_ROOT_RM = "recursive delete of root filesystem"


@pytest.mark.parametrize("command", [
    # Quoted delimiter, apostrophe in the body.
    "cat <<'EOF' > notes.txt\nit's done\nEOF\nrm -rf /",
    # Unquoted delimiter, unbalanced double quote in the body.
    'cat <<EOF > notes.txt\nshe said "hi\nEOF\nrm -rf /',
    # <<- strips leading tabs from the terminator line.
    "cat <<-'EOF' > notes.txt\n\tit's done\n\tEOF\nrm -rf /",
    # Two heredocs on one command: both bodies end before the next command.
    "cat <<'A' <<'B' > notes.txt\nit's\nA\nfine\nB\nrm -rf /",
    # A later command on the same line as a list operator after the heredoc body.
    "python3 - <<'PY'\nprint('it''s')\nprint(\"x)\nPY\necho done; rm -rf /",
])
def test_unbalanced_quote_in_heredoc_body_does_not_hide_a_hardline_command(command):
    assert detect_hardline_command(command) == (True, _ROOT_RM)


def test_unbalanced_quote_in_heredoc_body_does_not_hide_a_dangerous_command():
    # Command-position rule (_CMDPOS): quoted prose mentioning it is data, a real command is not.
    command = "cat <<'EOF' > notes.txt\nit's done\nEOF\nnpm uninstall left-pad"
    assert detect_dangerous_command(command) == (True, "package manager uninstall", "package manager uninstall")


@pytest.fixture
def deny_config(monkeypatch):
    state = {"config": {"mode": "manual", "deny": []}}
    monkeypatch.setattr(approval_context, "_get_approval_config", lambda: state["config"])

    def set_deny(patterns):
        state["config"] = {"mode": "manual", "deny": list(patterns)}
    return set_deny


def test_unbalanced_quote_in_heredoc_body_does_not_hide_a_user_deny_rule(deny_config):
    deny_config(["rm *"])
    command = "cat <<'EOF' > notes.txt\nit's done\nEOF\nrm -rf build"
    assert mod._match_user_deny_rule(command) == "rm *"


@pytest.mark.parametrize("command", [
    "cat <<'EOF' > notes.txt\nit's done\nEOF\necho ok",
    "cat <<EOF > notes.txt\nshe said \"hi\nEOF\nls -la",
])
def test_benign_command_after_a_heredoc_stays_allowed(command):
    assert detect_hardline_command(command) == (False, None)
    assert detect_dangerous_command(command) == (False, None, None)


def test_shell_heredoc_bodies_are_still_scanned():
    """The bodies stay visible: ``bash`` executes what it reads from the heredoc."""
    assert detect_hardline_command("bash <<'EOF'\nrm -rf /\nEOF") == (True, _ROOT_RM)
