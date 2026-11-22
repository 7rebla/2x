# Docling results for the tests

Real answers of docling-serve, converted from the free test documents in
[`testdata/klein/`](../../../../testdata/klein/README.md). The tests of the
Docling client (work order 041) and of the section builder (work order 043)
read them; no test needs a running Docling for that. Each file holds only the
DoclingDocument (`document.json_content` of the answer), written by
`check_docling --json-out -` with one space of indentation.

| File | Source | License | Pages |
| --- | --- | --- | --- |
| `betrsichv-p1-5.docling.json` | `testdata/klein/recht/BetrSichV.pdf`, pages 1 to 5 | public domain (official work, section 5 (1) UrhG) | 5 |
| `sftp-backup.docling.json` | `testdata/klein/opnsense/markdown/sftp-backup.md` | BSD-2-Clause, copyright Deciso B.V. and contributors; license text in [`testdata/klein/opnsense/LICENSE`](../../../../testdata/klein/opnsense/LICENSE) | none (Markdown) |

Origin, version and checksum of both sources are in
[`testdata/klein/manifest.yaml`](../../../../testdata/klein/manifest.yaml).

## Docling version

- Image `quay.io/docling-project/docling-serve-cpu:v1.38.2`, pinned by digest
  in `deploy/compose/compose.yaml`
- docling-serve 1.38.2, docling 2.142.1, docling-core 2.104.0 (from `/version`)
- DoclingDocument schema version 1.10.0 (field `version` in the files)
- Request: `to_formats=json`, `ocr_preset=rapidocr`,
  `image_export_mode=placeholder`, `document_timeout=7200`; the PDF with
  `page_range` 1 and 5. The upload is named `upload.pdf` or `upload.md`,
  which is why `name` is `upload`.

Converted on 2026-11-22. Two runs gave byte-identical files: the
DoclingDocument has no time stamps, and `origin.binary_hash` depends on the
content only.

## Commands

Run in Git Bash from the repository root with the services and `docling`
running (`api` reaches Docling, `backend-dev` does not). Redirect only in Git
Bash, not in PowerShell, so that no byte order mark or other encoding gets in.

```sh
docker compose exec -T api python manage.py check_docling --convert - --page-range 1 5 --json-out - < testdata/klein/recht/BetrSichV.pdf > backend/tests/ingest/fixtures/betrsichv-p1-5.docling.json
docker compose exec -T api python manage.py check_docling --convert - --suffix .md --json-out - < testdata/klein/opnsense/markdown/sftp-backup.md > backend/tests/ingest/fixtures/sftp-backup.docling.json
```

Only documents from `testdata/klein/` are converted here, never vendor
documents from `testfactory/extern/`.
