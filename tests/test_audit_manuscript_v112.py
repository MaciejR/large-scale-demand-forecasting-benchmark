import re
from pathlib import Path


def test_manuscript_version_regexes_do_not_match_v112():
    script = Path("tools/audit_manuscript_v112.sh").read_text()

    assert "v1\\.1([^0-9]|$)" in script
    assert "v1\\.2([^0-9]|$)" in script
    assert not re.search(r"v1\.1([^0-9]|$)", "GitHub release v1.12")
    assert not re.search(r"v1\.2([^0-9]|$)", "GitHub release v1.12")


def test_manuscript_version_regexes_match_stale_versions():
    assert re.search(r"v1\.1([^0-9]|$)", "Superseded v1.1 manuscript")
    assert re.search(r"v1\.2([^0-9]|$)", "Superseded v1.2 manuscript")
