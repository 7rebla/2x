# CI questions and the injection probe

Inputs of `tests/answers/test_ci_questions.py` (work order 135): the small question set that runs the whole answer chain in CI against recorded model answers (E-10).

| File | What it is | Origin and licence |
| --- | --- | --- |
| `ci_questions.json` | The question set: id, question (German, own words), kind (`fact`, `no-evidence`, `injection`), the document and page or heading path that answer it, a short `evidence` string to find that section, `keywords` for the keyword search with the AI features off, key facts, an optional scope (`scope_document`) and, for the probe, the forbidden word | Self-written. `evidence` and the key facts are a few words of the free documents below |
| `injection.md` | A short test text with an embedded instruction to the model (ignore the rules, print a word, a picture, a link and a password) next to one harmless fact | Self-written test text, no real device and no vendor document (D16) |

The sections the questions are asked against come from the Docling fixtures in [`../../ingest/fixtures/`](../../ingest/fixtures/README.md): `betrsichv-p1-5.docling.json` (BetrSichV pages 1 to 5, public domain as an official work, section 5 (1) UrhG) and `sftp-backup.docling.json` (OPNsense documentation, BSD-2-Clause). Both come from [`testdata/klein/`](../../../../testdata/klein/README.md); origin, version and checksum are in its `manifest.yaml`. Nothing here comes from `testfactory/` or from a vendor manual, and none of the 11 test questions of `testfactory/questions.yaml` is part of the set: those run only locally (`evaluate_answers`).

## Question set format

```json
{
  "schema_version": 1,
  "questions": [
    {
      "id": "ci-fact-1",
      "kind": "fact",
      "question": "...",
      "document": "betrsichv",
      "page": 1,
      "evidence": "...",
      "key_facts": ["..."],
      "key_fact_alternatives": {"...": ["..."]}
    }
  ]
}
```

- `document` is an id of the test (`betrsichv`, `sftp-backup`, `injection`), not a checksum: the test uploads stand-in bytes, so it maps the id to the checksum of the version it created.
- `page` (PDF) or `heading_path` (Markdown, prefix of the section's path) is the expected place; it is compared with the rules of `evaluate_answers` (`twox.answers.evaluation`, `matching_place`).
- There is no contradiction question: the two fixtures hold no real contradiction, and a made-up one is not allowed (guard rail 9). That path is covered with `FakeChatModel` in `test_citations.py` and `test_service.py`.
