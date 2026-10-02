import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

import runs

REPO = Path(__file__).resolve().parents[2]
TOOLKIT = REPO / "guide" / "toolkit"
LEDGER = REPO / "tests" / "fixtures" / "ledger" / "progress.md"


@pytest.fixture
def workspace(tmp_path):
    ws = tmp_path / ".superpowers" / "sdd" / "plan"
    ws.mkdir(parents=True)
    shutil.copy(LEDGER, ws / "progress.md")
    return ws


def test_parse_ledger_identity_and_tasks():
    led = runs.parse_ledger(LEDGER)
    assert led.plan == "docs/guide/plan.md"
    assert sorted(led.tasks) == [1, 2, 3]
    t1, t2, t3 = led.tasks[1], led.tasks[2], led.tasks[3]
    assert (t1.status, t1.verdict, t1.fix_rounds, t1.commits) == ("complete", "clean", 0, "1111111..2222222")
    assert (t2.status, t2.verdict, t2.fix_rounds, t2.commits) == ("complete", "clean", 1, "2222222..4444444")
    assert t3.status == "fix round"
    assert t3.verdict == "Needs fixes"
    assert t3.fix_rounds == 1
    assert t3.commits == "5555555..6666666"


def test_rulings_deferred_and_dispatches():
    led = runs.parse_ledger(LEDGER)
    assert [r.id for r in led.rulings] == ["R1", "R2"]
    assert led.rulings[1].text.startswith("the walkthrough's admin UI")
    assert len(led.deferred) == 1 and led.deferred[0].task == 2
    assert len(led.rejected) == 1 and "7070" in led.rejected[0]
    # Task 1: one review; Task 2: review plus one re-review; Task 3: review plus one re-review.
    assert led.review_dispatches == 5


def test_identity_with_em_dash(tmp_path):
    text = LEDGER.read_text().replace("# SDD ledger - plan:", f"# SDD ledger {chr(0x2014)} plan:", 1)
    path = tmp_path / "progress.md"
    path.write_text(text)
    assert runs.parse_ledger(path).plan == "docs/guide/plan.md"


def test_resume_point():
    led = runs.parse_ledger(LEDGER)
    assert runs.resume_point(led) == 3
    assert runs.resume_point(led, total=3) == 3


def test_resume_point_after_all_seen_complete(tmp_path):
    path = tmp_path / "progress.md"
    path.write_text("# SDD ledger - plan: docs/guide/plan.md\n"
                    "Task 1: complete (commits a..b, review clean)\n"
                    "Task 2: complete (commits b..c, review clean)\n")
    led = runs.parse_ledger(path)
    assert runs.resume_point(led, total=4) == 3
    assert runs.resume_point(led, total=2) is None
    assert runs.resume_point(led) is None


def test_real_ledger_shapes(tmp_path):
    lines = [
        "# SDD ledger - plan: docs/plans/x.md",
        "Task 14: fix round 1/5 dispatched to original implementer before the task review (fix base c6a15c5)",
        "Task 14: fix round 1/5 done (commit 6f27879: copy-images step)",
        "Task 14: review Needs fixes (1 Important: generate-keys). Fix round 2/5 dispatched (fix base 6f27879)",
        "Task 14: fix round 2/5 (1 addressed, 0 open; commits 6f27879..309d008)",
        "Task 14: complete (commits 61046fa..309d008, review clean after 2 fix rounds)",
        "Task 15: parked: label overlap - Ruling: acceptable at 2x",
        "Task 15: complete (commits 309d008..2615fd6, 1 parked)",
        "Ruling R3 is moot: the lighter variant removed claim references.",
        "Task 16: Ruling: skip prose check on table pages - cost if wrong: minor",
        "Task 23: review dispatched (package review-6d2f1ce..73c7157.diff)",
    ]
    path = tmp_path / "progress.md"
    path.write_text("\n".join(lines) + "\n")
    led = runs.parse_ledger(path)
    assert led.tasks[14].fix_rounds == 2
    assert led.tasks[14].status == "complete"
    assert led.tasks[15].parked == 1
    assert led.tasks[15].verdict == "parked"
    assert led.tasks[23].status == "in review"
    ids = [r.id for r in led.rulings]
    assert "R3" in ids and len(ids) == 3
    assert any(r.task == 16 for r in led.rulings)


def test_summary_lists_tasks_rulings_and_findings(render_fixture_guide, workspace):
    root = render_fixture_guide
    runs.findings_add(root, {"source": "mini", "kind": "doc-drift",
                             "locations": [{"ref": "README.md:7", "quote": "The service listens on port 8080 by default."}],
                             "summary": "README states port 8080, the default config uses 9090.",
                             "evidence": "config/defaults.yaml:3 sets port: 9090"})
    out = runs.summary(root, workspace, "2026-10-01-create", command="create", rigor="standard",
                       model="claude-opus-5-5", effort="high")
    assert out == root / "runs" / "2026-10-01-create.md"
    text = out.read_text()
    for task in ("| 1 |", "| 2 |", "| 3 |"):
        assert task in text
    assert "| 3 | fix round | Needs fixes | 1 |" in text
    assert "R1" in text and "R2" in text
    assert "admin/install.md repeats the bind address" in text
    assert "UF-1" in text
    assert "7070" in text
    assert "claude-opus-5-5" in text
    assert "Review dispatches | 5" in text
    assert "{{" not in text
    assert "Not run" in text
    assert chr(0x2014) not in text and chr(0x2013) not in text


def test_summary_validation_counts(render_fixture_guide, workspace):
    root = render_fixture_guide
    vdir = root / ".guide" / "runs" / "2026-10-01-validate"
    vdir.mkdir(parents=True)
    (vdir / "validation.md").write_text(
        "| page | line | command | tier | classification | outcome |\n|---|---|---|---|---|---|\n"
        "| a.md | 3 | oc get pods | read-only | query | match |\n"
        "| a.md | 9 | oc get ns | read-only | query | mismatch |\n"
        "| b.md | 4 | make x | read-only | mutating | skipped |\n")
    text = runs.summary(root, workspace, "2026-10-01-validate").read_text()
    assert "match: 1" in text and "mismatch: 1" in text and "skipped: 1" in text


def test_findings_add_assigns_ids(render_fixture_guide):
    root = render_fixture_guide
    base = {"source": "mini", "kind": "doc-drift", "locations": [{"ref": "README.md:7"}],
            "summary": "s", "evidence": "e"}
    assert runs.findings_add(root, dict(base)) == "UF-1"
    assert runs.findings_add(root, dict(base, kind="stale-reference")) == "UF-2"
    data = yaml.safe_load((root / "findings" / "upstream.yaml").read_text())
    assert [f["id"] for f in data["findings"]] == ["UF-1", "UF-2"]
    assert all(f["status"] == "collected" for f in data["findings"])


def test_findings_add_rejects_invalid(render_fixture_guide):
    with pytest.raises(runs.FindingError) as err:
        runs.findings_add(render_fixture_guide, {"source": "nope", "kind": "rant", "locations": [],
                                                 "summary": "s", "evidence": "e"})
    msg = str(err.value)
    assert "source" in msg and "kind" in msg
    assert not (render_fixture_guide / "findings" / "upstream.yaml").exists()


def test_cli_findings_add_flags_and_json(render_fixture_guide, tmp_path):
    root = render_fixture_guide
    proc = subprocess.run([sys.executable, str(TOOLKIT / "runs.py"), "findings-add", "--root", str(root),
                           "--source", "mini", "--kind", "doc-drift", "--location", "README.md:7",
                           "--quote", "listens on port 8080", "--summary", "Wrong port.", "--evidence", "9090"],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "UF-1"
    payload = tmp_path / "f.json"
    payload.write_text(json.dumps({"source": "mini", "kind": "naming-ux", "locations": [{"ref": "Makefile:3"}],
                                   "summary": "Confusing target name.", "evidence": "install only echoes"}))
    proc = subprocess.run([sys.executable, str(TOOLKIT / "runs.py"), "findings-add", "--root", str(root),
                           "--json", str(payload)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "UF-2"
    data = yaml.safe_load((root / "findings" / "upstream.yaml").read_text())
    assert data["findings"][0]["locations"][0]["quote"] == "listens on port 8080"


def test_cli_summary_and_resume(render_fixture_guide, workspace):
    root = render_fixture_guide
    proc = subprocess.run([sys.executable, str(TOOLKIT / "runs.py"), "summary", "--root", str(root),
                           "--workspace", str(workspace), "--run-id", "2026-10-01-create",
                           "--command", "create", "--rigor", "fast"], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert (root / "runs" / "2026-10-01-create.md").is_file()
    proc = subprocess.run([sys.executable, str(TOOLKIT / "runs.py"), "resume", "--workspace", str(workspace)],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "3"


def test_next_run_id(tmp_guide):
    first = runs.next_run_id(tmp_guide, "create", date="2026-10-01")
    assert first == "2026-10-01-create"
    (tmp_guide / "runs").mkdir()
    (tmp_guide / "runs" / f"{first}.md").write_text("x")
    assert runs.next_run_id(tmp_guide, "create", date="2026-10-01") == "2026-10-01-create-2"


def test_cli_run_id(tmp_guide):
    import subprocess
    import sys
    toolkit = Path(__file__).resolve().parents[2] / "guide" / "toolkit"
    proc = subprocess.run([sys.executable, str(toolkit / "runs.py"), "run-id", "--command", "evolve",
                           "--root", str(tmp_guide)], capture_output=True, text=True, check=True)
    assert proc.stdout.strip().endswith("-evolve")


def test_summary_without_ledger(tmp_path, render_fixture_guide):
    """Commands without a superpowers run (validate) still get a run summary."""
    out = runs.summary(render_fixture_guide, tmp_path / "no-workspace", "2026-10-01-validate",
                       command="validate")
    text = out.read_text()
    assert "2026-10-01-validate" in text and "no tasks recorded" in text


def test_resume_without_ledger_uses_plan_path_marker(tmp_path):
    root = tmp_path / "g"
    (root / "docs" / "guide").mkdir(parents=True)
    (root / "docs" / "guide" / "plan.md").write_text("# Plan\n\n### Task 1: index\n\n### Task 2: install\n")
    ws = root / ".superpowers" / "sdd" / "plan"
    ws.mkdir(parents=True)
    (ws / "plan-path").write_text("docs/guide/plan.md\n")
    toolkit = Path(__file__).resolve().parents[2] / "guide" / "toolkit"
    proc = subprocess.run([sys.executable, str(toolkit / "runs.py"), "resume", "--workspace", str(ws),
                           "--root", str(root)], capture_output=True, text=True, check=True)
    assert proc.stdout.strip() == "1"


def test_skipped_reviews_are_not_dispatches(tmp_path):
    ledger = tmp_path / "progress.md"
    ledger.write_text(
        "# SDD ledger - plan: docs/guide/plan.md\n\n"
        "Task 1: dispatched (base aaaaaaa)\n"
        "Task 1: review skipped (rigor fast)\n"
        "Task 1: complete (commits aaaaaaa..bbbbbbb, no review)\n"
    )
    led = runs.parse_ledger(ledger)
    assert led.review_dispatches == 0
    assert led.tasks[1].status == "complete"
