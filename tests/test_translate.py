"""Focused tests for validated, local subtitle translation."""

from unittest.mock import patch

import pytest

from app.errors import ProcessingCancelled
from app.translate import (
    TranslationError,
    _ollama_translate_batch,
    translate_srt_content,
    translate_srt_file,
)


def test_ollama_batch_validates_ids_and_restores_styles():
    response = {"message": {"content": "[0001] Olá Mundo"}}
    with patch("app.translate._post_json", return_value=response):
        translated = _ollama_translate_batch(["<i>Hello</i>\nWorld"], "en", "pt-BR")

    assert translated == ["<i>Olá</i>\nMundo"]


def test_ollama_batch_rejects_incomplete_response():
    response = {"message": {"content": ""}}
    with patch("app.translate._post_json", return_value=response):
        with pytest.raises(TranslationError, match="incomplete"):
            _ollama_translate_batch(["Hello"], "en", "pt-BR")


def test_ollama_batch_uses_official_translategemma_prompt():
    response = {"message": {"content": "[0001] Olá"}}
    with patch("app.translate._post_json", return_value=response) as post:
        _ollama_translate_batch(["Hello"], "en", "pt-BR")

    payload = post.call_args.args[1]
    assert "format" not in payload
    assert payload["messages"] == [
        {
            "role": "user",
            "content": payload["messages"][0]["content"],
        }
    ]
    prompt = payload["messages"][0]["content"]
    assert prompt.startswith(
        "You are a professional English (en) to Brazilian Portuguese (pt-BR) translator."
    )
    assert "\n\n\n[0001] Hello" in prompt


def test_translation_rejects_mostly_unchanged_english():
    raw = (
        "1\n00:00:01,000 --> 00:00:02,000\nHello world\n\n"
        "2\n00:00:03,000 --> 00:00:04,000\nGood morning\n"
    )
    with patch(
        "app.translate._translate_batch_with_fallback",
        side_effect=lambda texts, _source, _target, _stop: texts,
    ):
        with pytest.raises(TranslationError, match="unchanged"):
            translate_srt_content(raw)


def test_translation_honors_cancellation_before_first_batch():
    raw = "1\n00:00:01,000 --> 00:00:02,000\nHello world\n"
    with pytest.raises(ProcessingCancelled):
        translate_srt_content(raw, stop_requested=lambda: True)


def test_translation_prepends_visible_versioned_watermark():
    raw = "1\n00:00:10,000 --> 00:00:12,000\nHello world\n"
    with patch(
        "app.translate._translate_batch_with_fallback",
        return_value=["Olá, mundo"],
    ):
        translated = translate_srt_content(raw)

    assert translated.startswith(
        "1\n00:00:01,000 --> 00:00:04,000\n"
        "Tradução automática • modelo: translategemma:12b\n"
        "Subtitle Engine v0.3.0 • prompt: translategemma-v1\n\n"
        "2\n00:00:10,000 --> 00:00:12,000\nOlá, mundo"
    )


def test_translate_file_does_not_publish_partial_output(tmp_path):
    source = tmp_path / "source.srt"
    target = tmp_path / "target.pt-BR.srt"
    source.write_text("1\n00:00:01,000 --> 00:00:02,000\nHello world\n")

    with patch("app.translate.translate_srt_content", side_effect=TranslationError("bad batch")):
        with pytest.raises(TranslationError):
            translate_srt_file(source, target)

    assert not target.exists()
def test_translate_file_publishes_only_subtitle(tmp_path):
    source = tmp_path / "source.srt"
    target = tmp_path / "target.pt-BR.srt"
    source.write_text("1\n00:00:01,000 --> 00:00:02,000\nHello world\n")
    translated = "1\n00:00:01,000 --> 00:00:02,000\nOlá, mundo\n"

    with patch("app.translate.translate_srt_content", return_value=translated):
        translate_srt_file(source, target)

    assert target.read_text() == translated
    assert set(tmp_path.iterdir()) == {source, target}
