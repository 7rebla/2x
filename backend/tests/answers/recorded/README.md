# Recorded model answers for CI

`ci_questions.json` holds the answers of the real chat model to the CI questions (`../fixtures/ci_questions.json`), recorded once locally. In CI, `tests/answers/test_ci_questions.py` plays them back with `ReplayChatModel` (`twox/answers/replay.py`), so the whole answer chain runs on every push without a model and without network: context selection, prompt, citation check, refusal and scope (E-10, work order 135). CI checks prompt, context and the handling of a fixed model answer; it does not check the model itself.

## Format

```json
{
  "schema_version": 1,
  "model": "<TWOX_CHAT_MODEL of the recording>",
  "model_digest": "<digest from /api/tags>",
  "prompt_version": "<prompt_version()>",
  "recorded_on": "YYYY-MM-DD",
  "settings": {"temperature": 0.0, "seed": 135, "max_tokens": 1024, "reasoning_effort": "none"},
  "entries": [
    {
      "question_id": "ci-fact-1",
      "key": "<recording_key>",
      "sources": [{"n": 1, "sha256": "...", "ordinal": 0}],
      "chunks": ["...", "..."]
    }
  ]
}
```

- `key` is SHA-256 over `prompt_version()`, the model name and the messages to the model in canonical JSON. A changed prompt template, a changed context or another model gives another key; the test then fails with `RecordingMissingError` and `re-record: manage.py record_answers` instead of playing an old answer.
- `chunks` are the text pieces of the model, nothing else. Prompts and section texts are not stored; the test builds them again from the fixtures. `sources` names number, document checksum and section ordinal of each source the model saw (the checksums are those of the stand-in bytes the test uploads).
- The layout is fixed (two spaces, keys in this order, entries sorted by question id and key), so a second recording with the same answers is byte-identical.

## Origin of the texts

The model answered questions about sections of `testdata/klein` only (BetrSichV pages 1 to 5, public domain; OPNsense documentation, BSD-2-Clause) and about the self-written injection text `../fixtures/injection.md`. Details and licences: [`../fixtures/README.md`](../fixtures/README.md). Before a recording is committed, read it through: no foreign links, no names of persons, no paths.

## Recording again

Only locally, in `backend-dev`, with the chat model on the host (Ollama, reached through `host.docker.internal`) and the AI features on:

```sh
docker compose run --rm -e TWOX_CHAT_MODEL=gemma4:31b-it-qat backend-dev python manage.py record_answers
```

The command runs `tests/answers/test_ci_questions.py` with `TWOX_RECORD_ANSWERS=1`: the same set-up as in CI, only the chat model is real (temperature 0, seed 135, reasoning off). Every check runs as well; the file is written only when every question that asked the model passed its checks, otherwise the run fails and names the question. Record again after every change of the prompt (`prompt_version()`), of the context selection or of the fixtures, and commit only a recording made with a chat model whose licence and digest are checked at the source (D1). Do not record while another measurement uses the same model.
