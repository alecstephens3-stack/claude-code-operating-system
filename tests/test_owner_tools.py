import json
import stat

import pytest

import add_key
import check_design_system as ds
import open_checklist as oc

SPEC = {"id": "dns-records", "title": "Point the <domain>", "intro": "Ten minutes.",
        "steps": [{"text": "Open DNS", "detail": "At the registrar.", "copy": "https://example.com/dns"},
                  {"text": "Add the A record"}]}


# add_key ---------------------------------------------------------------------

def test_saves_without_printing_the_value(tmp_path, capsys):
    env = tmp_path / ".env"
    assert add_key.main(["REPORT_API_KEY", "reporting key"], ask=lambda label: "s3cret-value", env=env) == 0
    out = capsys.readouterr().out
    assert "s3cret-value" not in out and "12 characters" in out
    assert env.read_text() == "REPORT_API_KEY=s3cret-value\n"
    assert stat.S_IMODE(env.stat().st_mode) == 0o600


def test_replaces_an_existing_value_and_keeps_the_rest(tmp_path):
    env = tmp_path / ".env"
    env.write_text("OTHER=1\nREPORT_API_KEY=old\n")
    add_key.main(["REPORT_API_KEY"], ask=lambda label: "new", env=env)
    assert env.read_text() == "OTHER=1\nREPORT_API_KEY=new\n"


@pytest.mark.parametrize("answer", [None, ""])
def test_cancel_or_empty_saves_nothing(tmp_path, answer):
    env = tmp_path / ".env"
    assert add_key.main(["REPORT_API_KEY"], ask=lambda label: answer, env=env) == 1
    assert not env.exists()


@pytest.mark.parametrize("name", ["lower", "1KEY", "KEY=X", ""])
def test_bad_names_are_refused_before_asking(tmp_path, name):
    asked = []
    assert add_key.main([name], ask=lambda label: asked.append(label) or "x", env=tmp_path / ".env") == 2
    assert asked == []


# open_checklist ----------------------------------------------------------------

def test_render_escapes_and_fills_every_placeholder():
    page = oc.render(SPEC)
    assert "Point the &lt;domain&gt;" in page and "{{" not in page
    assert page.count('class="ds-step"') == 2
    assert '<code>https://example.com/dns</code><button type="button">Copy</button>' in page
    assert '"checklist:dns-records"' in page


def test_rendered_page_passes_the_design_system_guard():
    cfg = json.loads((ds.DEFAULT_CONFIG).read_text())
    assert ds.judge(oc.render(SPEC), "artifacts/checklists/dns-records.html", cfg) is None


@pytest.mark.parametrize("spec", [{**SPEC, "id": "Bad Id"}, {**SPEC, "steps": []}])
def test_bad_specs_are_refused(spec):
    with pytest.raises(oc.SpecError):
        oc.render(spec)


def test_main_writes_the_page(tmp_path):
    spec = tmp_path / "steps.json"
    spec.write_text(json.dumps(SPEC))
    assert oc.main([str(spec), "--out", str(tmp_path), "--no-open"]) == 0
    assert (tmp_path / "dns-records.html").exists()
