# Prompt history

Translation prompts are immutable runtime assets under `app/prompts/`. The application reads the selected file directly, so this history cannot silently diverge from production.

| ID | Model | Protocol | Status |
|---|---|---|---|
| `translategemma-v1` | `translategemma:12b` | Official TranslateGemma instruction; one `user` message; numbered cue markers; temperature `0` | active |

## Request sent to Ollama

The active template is [`app/prompts/translategemma-v1.txt`](../app/prompts/translategemma-v1.txt). At runtime, placeholders are filled and `{text}` is replaced with contiguous cues formatted as `[0001] text`.

```json
{
  "model": "<OLLAMA_MODEL>",
  "stream": false,
  "keep_alive": "<OLLAMA_KEEP_ALIVE>",
  "options": {"temperature": 0},
  "messages": [{"role": "user", "content": "<rendered prompt>"}]
}
```

There is no `system` message or JSON response format. The response must contain one `[NNNN]` line for every input cue.

## Creating the next version

1. Copy the current template to a new sequential filename, such as `translategemma-v2.txt`.
2. Change `PROMPT_ID` in `app/prompt.py`; never edit an older template.
3. Add a row here describing the model, protocol, motivation, and evaluation result.
4. Update tests and compare both versions on the same representative subtitle samples before deployment.

The visible watermark records `promptId`, allowing every generated subtitle to be traced
back to the exact template committed in this repository without an orphanable sidecar.
