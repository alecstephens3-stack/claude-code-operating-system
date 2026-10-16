import pytest

import copy_check as cc

RULES = cc.load_rules()
PROOF = "Order entry went from 25 minutes to 6 minutes. About 8 hours a week. Errors fell 40%."


def run(text, profile="artifact", corpus=PROOF):
    return cc.check(text, profile, RULES, corpus)


def codes(lines):
    return {line.split()[0] for line in lines}


def test_em_and_en_dashes_fail():
    hard, _ = run("Fast \u2014 and cheap. Pages 3\u20135.")
    assert sum("DASH" in h for h in hard) == 2


def test_banned_phrase_fails_whole_phrase_only():
    assert "BANNED" in codes(run("Let's circle back next week.")[0])
    assert run("The synergyless plan.")[0] == []


def test_word_family_matches_whole_words_only():
    assert "BANNED" in codes(run("Typing orders eats the morning.")[0])
    assert run("A great treat for the team.")[0] == []


def test_retired_tool_fails_when_sending_but_is_verify_on_a_page():
    hard, _ = run("We moved off the legacy scheduler.", profile="email")
    assert any("RETIRED" in h for h in hard)
    hard, verify = run("We moved off the legacy scheduler.", profile="artifact")
    assert not any("RETIRED" in h for h in hard)
    assert any("RETIRED" in v for v in verify)


def test_proven_numbers_pass_across_spellings():
    _, verify = run("It saves 8 hrs a week and errors fell 40 percent.")
    assert verify == []


def test_unproven_number_is_verify_not_fail():
    hard, verify = run("It saves 15 hours a week.")
    assert hard == []
    assert any("15 hours" in v for v in verify)


def test_percentage_at_end_of_sentence_is_caught():
    _, verify = run("Errors fell 93%.")
    assert any("93%" in v for v in verify)


def test_bare_integers_are_not_claims():
    assert run("Pick one of 3 options.") == ([], [])


def test_no_proof_files_flags_everything():
    _, verify = run("Nothing here.", corpus="")
    assert any("no proof files" in v for v in verify)


def test_email_rules():
    good = "Hi there,\n\nThe screen is ready.\n\nThanks!\n"
    assert run(good, "email") == ([], [])
    hard, verify = run("Done! Ready! Shipped!", "email")
    assert any("WARMTH" in h for h in hard)
    assert {"OPENING", "CLOSE"} <= {v.split()[0] for v in verify}
    long = "Hi there,\n" + "word " * 210 + "\nThanks\n"
    assert any("LENGTH" in h for h in run(long, "email")[0])


def proposal(body):
    filler = " ".join(["Plain rules handle the fields that never change."] * 14)
    return f"{body} {filler} Would next week work?"


def test_proposal_passes_when_clean():
    assert run(proposal("Your team retypes every order by hand."), "proposal") == ([], [])


@pytest.mark.parametrize("text, code", [
    (proposal("I can fix your order entry."), "OPENING"),
    (proposal("Hello, your orders are retyped."), "OPENING"),
    (proposal("Your orders cost $500 to fix."), "PRICING"),
    (proposal("Your orders are retyped.").replace("Would next week work?", "Talk soon."), "CLOSE"),
    ("Too short. Would it help?", "LENGTH"),
])
def test_proposal_failures(text, code):
    assert code in codes(run(text, "proposal")[0])


def test_html_is_stripped_before_checking():
    page = "<style>.a{width:50%}</style><p>Errors fell 40%.</p><script>var x = 99;</script>"
    text = cc.strip_html(page)
    assert "50%" not in text and "99" not in text
    assert run(text) == ([], [])


def test_main_reads_proof_files_from_root(tmp_path, capsys):
    (tmp_path / "vault").mkdir()
    (tmp_path / "vault" / "proof.md").write_text("We returned 8 hours a week.")
    draft = tmp_path / "draft.txt"
    draft.write_text("Hi there,\n\nThat is 8 hours a week back.\n\nThanks\n")
    assert cc.main([str(draft), "--profile", "email", "--root", str(tmp_path)]) == 0
    assert "proof from 1 file(s)" in capsys.readouterr().out
