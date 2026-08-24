from app.audit import audit_cues
from app.srt import SrtCue


def cue(identifier: int, text: str) -> SrtCue:
    return SrtCue(str(identifier), f"00:00:{identifier:02d},000 --> 00:00:{identifier:02d},900", text)


def test_audit_detects_missing_unchanged_english_truncated_and_repeated():
    source = [
        cue(1, "We need to leave now"),
        cue(2, "Where are you going with all of the supplies?"),
        cue(3, "This sentence has many words and loses almost all of its original content"),
        cue(4, "Tell the captain we are ready"),
        cue(5, "Warn the crew before departure"),
        cue(6, "Nothing remains here"),
    ]
    translated = [
        cue(1, "We need to leave now"),
        cue(2, "Where are you going with all of our supplies?"),
        cue(3, "Perdemos."),
        cue(4, "Avise ao capitão que estamos prontos"),
        cue(5, "Avise ao capitão que estamos prontos"),
    ]

    kinds = [issue.kind for issue in audit_cues(source, translated)]

    assert "unchanged" in kinds
    assert "english" in kinds
    assert "truncated" in kinds
    assert "repeated" in kinds
    assert "missing" in kinds


def test_audit_accepts_natural_translation():
    source = [
        cue(1, "Mind your own business"),
        cue(2, "I'll be right back"),
        cue(3, "Fred: Paolo Cortazar"),
        cue(4, "The atmosphere above the impact site"),
    ]
    translated = [
        cue(1, "Cuide da sua vida"),
        cue(2, "Já volto"),
        cue(3, "Fred: Paolo Cortazar"),
        cue(4, "A atmosfera acima do local do impacto"),
    ]

    assert audit_cues(source, translated) == []
