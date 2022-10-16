import re
from subprocess import check_output


def test_show_help() -> None:
    output: str = check_output(["python3", "coolero.py", "-h"], encoding='UTF-8')
    assert "coolero" in output
    assert "help" in output


def test_show_version() -> None:
    pattern = re.compile(r'.*Coolero \d+\.\d+\.\d+.*')
    output: str = check_output(["python3", "coolero.py", "-v"], encoding='UTF-8')
    assert pattern.search(output)
