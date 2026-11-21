# Test factory

The test factory is the reference plant that 2x is developed and tested
against. It consists only of real equipment with matching public
documentation and real configuration. Only the composition is made up: which
plants stand in the factory and how they are connected.

Vendor documents are **not** part of this repository. The repository holds a
manifest that says where every document comes from, which software version it
belongs to, what its checksum is and under which terms it may be used. A
script loads the material onto the developer's machine.

## Folders and files

| Path | Purpose |
| --- | --- |
| `manifest.yaml` | One entry per document or source: origin, software version, checksum, terms of use, assigned device. Repositories are pinned to a fixed commit. |
| `manifest_tools.py` | Loads, validates and writes manifest files. Standard library only. |
| `fetch.py` | Loads everything with `fetch: auto` into `extern/` and verifies checksums; see "Fetching". Standard library only. |
| `layout/` | Structure of the test factory: device list (CSV), network plan, description. Written by the project itself. |
| `generated/` | Configurations produced by the project itself with original vendor software (URSim, OPNsense), each with its software version. |
| `extern/` | Downloaded vendor material. Ignored by Git, never committed. |
| `tests/` | Tests of the tools in this folder. |
| `mypy.ini` | Type checking configuration (`strict`), excludes `extern/` and `generated/`. |

The same manifest format is used by `testdata/klein/manifest.yaml`, which
describes the freely licensed documents that are checked in for the automatic
tests.

## Rules

- Vendor documents never go into the repository. The only exception is
  material under an explicitly free license.
- No larger excerpts from third-party manuals in published images or videos.
- The terms of use of every source are recorded in the manifest (`terms`),
  also for sources that are not downloaded, such as container images.
- Nothing from an employer.
- Configurations are never invented by hand. They come from the vendor or
  from the original software.

## Running the tools

Everything runs in containers; nothing is installed on the host. From the
repository root, with `TF` standing for
`docker compose -f deploy/compose/testfactory.yaml`:

```sh
# Check the manifest format (unmodified official Python image)
TF run --rm fetch python -m testfactory.manifest_tools check
TF run --rm fetch python -m testfactory.manifest_tools check --complete
TF run --rm fetch python -m testfactory.manifest_tools check testdata/klein/manifest.yaml

# Bring a manifest edited by hand into the canonical form
TF run --rm fetch python -m testfactory.manifest_tools format
TF run --rm fetch python -m testfactory.manifest_tools format --check

# Load and verify the material (see "Fetching")
TF run --rm fetch python -m testfactory.fetch --dry-run
TF run --rm fetch python -m testfactory.fetch

# Tests, with and without network
TF build check
TF run --rm check python -m unittest discover -s testfactory/tests -t . -v
TF run --rm check-offline python -m unittest discover -s testfactory/tests -t . -v

# Type checking
TF run --rm check mypy --config-file testfactory/mypy.ini testfactory
```

| Service | Image | Use |
| --- | --- | --- |
| `fetch` | official `python` image, unmodified | `manifest_tools.py` and `fetch.py`. The repository is mounted writable so that `extern/` can be filled and the manifest can be updated. |
| `check` | the same image plus the type checker | tests and type checking; the repository is mounted read-only |
| `check-offline` | as `check`, with `network_mode: none` | proof that the tests need no network |

The `fetch` service runs as `root` and writes into the mounted repository:
`fetch.py` below `extern/` and, with `--record`, into the manifest;
`manifest_tools format` into the manifest. On a Linux host the files created
this way belong to `root`. Everything else in the repository is left alone.

`testfactory` is a Python package. Import the tools as
`from testfactory import manifest_tools` and run them with
`python -m testfactory.manifest_tools`.

### `check`

`python -m testfactory.manifest_tools check [--complete] [PATH]`

- Checks the format of `PATH` (default `testfactory/manifest.yaml`).
- Exit code 0 and a line `PATH: OK (n entries)` if the file is valid.
- Exit code 1 otherwise. Every problem is printed on its own line with the
  entry ID and the field name, for example
  `testfactory/manifest.yaml: entry 'vendor-repository': field 'commit': must be a full commit ID (40 lower-case hexadecimal characters)`.
  Problems of the file itself are reported as `manifest`; an entry without a
  usable ID is named by its position (`#1` is the first entry).
- With `--complete` the check also fails if an entry with `fetch: auto` or
  `kind: local` has no checksum. Use it after the first fetch.

The command line accepts `https://` addresses only. There is no option to
relax this.

### `format`

`python -m testfactory.manifest_tools format [--check] [PATH]`

- Reads `PATH` (default `testfactory/manifest.yaml`) and writes it back in
  the canonical form described under "Notation". The content does not change,
  only the notation: order of the fields, indentation, line endings.
- Exit code 0 with `PATH: rewritten in canonical form` or
  `PATH: already in canonical form`.
- An invalid file is reported as by `check` (exit code 1) and left untouched.
- With `--check` nothing is written; exit code 1 if the file is not in the
  canonical form.

## Fetching

`fetch.py` loads the material that the manifest lists into the `root`
directory of the manifest, which is `testfactory/extern/` for the test
factory.

**Vendor documents never go into the repository.** `extern/` is ignored by
Git and must stay that way; never add files from it with `git add -f`. The
only exception is material under an explicitly free license, and that is
listed as `kind: local` and not loaded by this script.

```sh
# Show what would be done; loads and writes nothing
TF run --rm fetch python -m testfactory.fetch --dry-run

# Load every entry with fetch: auto and verify everything
TF run --rm fetch python -m testfactory.fetch

# Only some entries
TF run --rm fetch python -m testfactory.fetch --only ur5e-user-manual-de aps-repository

# Load nothing, only check what is there (works without network)
TF run --rm fetch python -m testfactory.fetch --verify

# First fetch: compute and store the checksums of entries that have none
TF run --rm fetch python -m testfactory.fetch --record
```

| Switch | Effect |
| --- | --- |
| (none) | Load every `auto` entry and verify it. A file or directory that is already there and has the right checksum is not loaded again, so a second run needs no network. |
| `--only ID [ID ...]` | Handle only these entries. An unknown ID ends the run with exit code 2. |
| `--verify` | Load nothing. Check what is there against the manifest. |
| `--record` | For entries without checksum: load, compute `sha256` or `tree_sha256`, `size_bytes` and `retrieved_on`, and write them into the manifest. The same is done for material fetched by hand that is present. A checksum that is already in the manifest is never changed. A `size_bytes` that an entry without checksum already has is an advance figure from research: the measured size replaces it, and a difference is reported as `SIZE DIFFERS` below the table (the material is kept; look into the difference). Review the diff of the manifest before committing it: the recorded checksum is what the source delivered at that moment. Not together with `--verify`. |
| `--dry-run` | Only show what would be done. Loads nothing, writes nothing, exit code 0. |
| `--strict` | Missing material that has to be fetched by hand leads to exit code 1. |
| `--manifest PATH` | Manifest file. Default `testfactory/manifest.yaml`. |
| `--dest PATH` | Directory to load into, instead of the `root` named in the manifest. |
| `--max-size MIB` | Largest allowed download. Default 2048 MiB. An extracted archive may be four times as large. |

### What happens per entry

| Entry | What the script does |
| --- | --- |
| `file`, `fetch: auto` | Loads `url` over HTTPS into a working file, computes the checksum while writing, and moves the file to `target` only if the checksum matches. Otherwise the download is discarded. |
| `git-archive`, `fetch: auto` | Loads the archive of the fixed commit from GitHub (`https://github.com/OWNER/REPOSITORY/archive/COMMIT.tar.gz`, the pattern from GitHub's documentation on source code archives), extracts it without its top-level directory, and moves it to `target` only if `tree_sha256` matches. No `git` is needed. Only repositories on `github.com` are supported. |
| `fetch: manual` | Never loaded. If the file or directory lies at `target` it is verified; otherwise the summary says where to get it (`landing_page`) and where to put it. |
| `local` | Never loaded; the checked-in file is verified against `sha256`. |
| `container-image`, `reference` | Nothing is loaded or checked; listed as `reference-only`. |

### Results

The run ends with a table: ID, result, HTTP status (if the server answered
with an error) and size in bytes, followed by one line of explanation for
every entry that needs one.

| Result | Meaning | Exit code |
| --- | --- | --- |
| `loaded` | Loaded now; checksum matches. | 0 |
| `recorded` | `--record`: checksum, size and date were written into the manifest. | 0 |
| `ok` | Already there; checksum matches. Nothing was loaded. | 0 |
| `reference-only` | Not something this script loads. | 0 |
| `manual` | Has to be fetched by hand and is not there yet. | 0, with a warning; 1 with `--strict` |
| `unverified` | Fetched by hand and present, but the manifest has no checksum yet. | 0 |
| `would-load`, `would-record` | `--dry-run`: what a real run would do. | 0 |
| `no-checksum` | `fetch: auto` without checksum. Nothing is loaded, because it could not be verified; use `--record` once. | 1 |
| `missing` | `--verify`: not there. Also: a `local` file that does not exist. | 1 |
| `mismatch` | The checksum differs from the manifest, or the checksum matches and `size_bytes` does not. A download is discarded; a file that is already in place is left as it is. | 1 |
| `failed` | Could not be loaded or extracted: server error (with HTTP status), unreachable server, size limit, refused address, unsafe archive, unsafe target. | 1 |

Exit code 0 means: every requested `auto` entry is present and its checksum
matches. Exit code 2: the manifest is not valid, an ID is unknown, or the
arguments are wrong; nothing was done.

### Safety

The script writes foreign files onto the machine, so it is deliberately
narrow:

- Only `https://`, also for every redirect (at most five). Every address
  goes through `manifest_tools.address_problem`, the one place that decides.
  The command line has no switch and no environment variable to relax this;
  `allow_insecure_loopback` exists only as a parameter in code, for the tests.
- Certificates are verified. Proxy settings of the environment are ignored.
  No cookies, no credentials. The `User-Agent` is the fixed text
  `twox-testfactory-fetch/1.0`.
- One download at a time. 60 seconds without data or one hour in total end
  an attempt. Unreachable or overloaded servers are tried three times with a
  pause; errors such as 404 are final.
- Downloads are written block by block and stop at the size limit, or at
  `size_bytes` if the manifest names one.
- Work happens in `<root>/.fetch-partial/`, which is removed afterwards.
  Nothing unverified ever lies at a `target`.
- Before writing, every target is checked against the root directory
  (`manifest_tools.checked_target_path`): no symbolic link in the chain, no
  way out of the root.
- Archives: member names must be clean relative paths below the one
  top-level directory, by the same rule as `target` (no `..`, no backslash,
  no `:` and therefore no drive letter). Regular files and directories
  additionally pass the `data` filter of the standard library; the small
  files that stand for links are checked against the resolved target
  directory before they are written. No link is ever created: a symbolic
  link in a repository is stored as a small file containing the link target,
  which is exactly how `tree_sha256` counts links. Hard links, devices and
  pipes make the archive fail, as do too many members or too much content.
- Loaded content is never imported or executed. ZIP files from vendors stay
  as they are.

## Manifest format

### Notation

The file is called `manifest.yaml` and is written in **JSON notation**. Every
JSON document is also a valid YAML document, so any YAML reader can read the
file, while the tools here need only the `json` module of the standard
library. Consequences:

- No comments. Use the field `notes` instead.
- A value that is not set is `null`. A missing field means the same as
  `null`. Empty strings are not allowed (exception: `language`).
- Unknown fields and duplicate keys are errors.
- Encoding UTF-8, line endings LF.

`manifest_tools.write_manifest` writes the one canonical form: every field,
in the order of the tables below, indented by two spaces, non-ASCII characters
unescaped, one newline at the end. Loading a file and writing it again gives
the same bytes, so automatic updates (checksums after the first fetch) produce
minimal diffs. Files edited by hand should be brought into this form as well.

### File

| Field | Required | Meaning |
| --- | --- | --- |
| `schema_version` | yes | Version of this format. Currently `1`, written as an integer (not `1.0`, not `"1"`). |
| `root` | yes | Directory that every `target` refers to, relative to the folder of the manifest file. `extern` for `testfactory/manifest.yaml`, `.` for `testdata/klein/manifest.yaml`. A relative path without `..`. |
| `entries` | yes | List of entries; may be empty. |

### Entry

| Field | Meaning |
| --- | --- |
| `id` | Unique within the file. Lower-case letters, digits and single hyphens, for example `ur5e-user-manual-de`. Required. |
| `title` | Human-readable title. Required. |
| `language` | `de`, `en`, or `""` if the source has no language or several. |
| `kind` | What the source is; see "Kinds". Required. |
| `fetch` | How the material gets onto the machine; see "Fetch modes". Required. |
| `url` | Address of the file itself. Required for `file` with `fetch: auto`; optional for `file` with `fetch: manual` (for example a download behind a form). For `reference` and `local` the address the material originates from. |
| `landing_page` | Page on which the vendor offers the material (for humans). Allowed for every kind. Required for `file` with `fetch: manual`. |
| `repository` | Address of a Git repository. |
| `branch` | Branch on which `commit` was found. Informational; the commit decides. |
| `commit` | Full commit ID, 40 lower-case hexadecimal characters. Short IDs, tags and branch names are not accepted. `repository`, `branch` and `commit` are required for `git-archive` and allowed for `reference` and `local`; `branch` and `commit` need `repository`. |
| `image` | Name of a container image, for example `vendor/simulator`. |
| `tag` | Tag of the image. |
| `digest` | Digest of the image: `sha256:` plus 64 hexadecimal characters. `image`, `tag` and `digest` are required for `container-image` and not allowed elsewhere. |
| `derived_from` | ID of the entry from which this file was produced. Only for `local`, optional. The tools check the form of the ID, not that the entry exists, because it may be listed in the other manifest file. |
| `generated_by` | The exact command that produced the file. Only for `local`, optional. |
| `software_version` | Software version of the plant or device that the material belongs to. |
| `document_version` | Edition or date of the document itself. |
| `version_source` | Where the version statements come from: title page, file name, tag, release page … |
| `sha256` | SHA-256 of the file, 64 lower-case hexadecimal characters. For `file` and `local`. Required for `local`; for `file` it may be `null` until the first fetch. |
| `tree_sha256` | Checksum of the extracted repository tree, see "Tree checksum". Only for `git-archive`; may be `null` until the first fetch. |
| `size_bytes` | Size in bytes (for `git-archive`: sum of all files; for `reference`: the size the source states, for information). Optional, for `file`, `git-archive`, `reference` and `local`. |
| `target` | Where the file (or, for `git-archive`, the directory) lies: a relative path below `root` with forward slashes, without `..`. Required for `file`, `git-archive` and `local`, not allowed otherwise. Unique within the file, and no target may lie inside the target of another entry (`vendor/repo` and `vendor/repo/a.pdf` collide, `vendor/repo` and `vendor/repo-2` do not). |
| `terms` | Terms of use; see below. Required. |
| `assigned_to` | List of `plant_id` or `device_id` values from `layout/devices.csv` that the material belongs to. May be empty. |
| `retrieved_on` | Date of the download or of the last check of the source, `YYYY-MM-DD`. |
| `notes` | Free text; takes the place of comments. |

### Terms of use (`terms`)

| Field | Required | Meaning |
| --- | --- | --- |
| `holder` | yes | Rights holder. |
| `license` | yes | SPDX identifier (for example `BSD-2-Clause`), or `proprietary`, `none-stated` (no license found at the source) or `public-domain`. |
| `redistribution` | yes | `true` if the material may be passed on, otherwise `false`. `kind: local` is only for material where this is `true`. |
| `terms_url` | no | Address of the license or terms text. |
| `note` | yes | The terms of use in one sentence. |
| `checked_on` | if `verified` | Date on which the terms were looked at, `YYYY-MM-DD`. |
| `verified` | yes | `true` = checked against the original text at the source; `false` = not yet checked. |

### Kinds

| `kind` | Meaning | Allowed `fetch` | Required fields |
| --- | --- | --- | --- |
| `file` | A single file loaded over HTTPS. | `auto`, `manual` | `target`; `url` with `auto`, `landing_page` with `manual` |
| `git-archive` | The state of a Git repository at a fixed commit. | `auto`, `manual` | `repository`, `branch`, `commit`, `target` |
| `container-image` | A container image; only name, tag and digest are recorded. It is not loaded. | `none` | `image`, `tag`, `digest` |
| `reference` | A pointer to a source that is not loaded. | `none` | at least one of `url`, `landing_page`, `repository` |
| `local` | A file that is checked in below `root`. Only for explicitly free material. | `none` | `target`, `sha256` |

### Fetch modes

| `fetch` | Meaning |
| --- | --- |
| `auto` | The fetch script loads the material and verifies the checksum. |
| `manual` | A person loads the material (for example behind a form); the tools only verify the file. |
| `none` | Nothing is loaded. |

### Addresses

`url`, `landing_page`, `repository` and `terms.terms_url` must be absolute
`https://` addresses without user name or password. The rule lives in exactly
one function, `manifest_tools.address_problem`.

For tests that serve files from a local server,
`load_manifest(path, allow_insecure_loopback=True)` additionally accepts
`http://127.0.0.1` and `http://localhost`. The switch can only be set in
code; the command line never sets it.

## Tree checksum (`tree_sha256`)

The checksum of a `git-archive` entry is computed over the extracted files,
not over the archive. It therefore does not depend on how the hosting service
packs the archive.

1. Take every file below the directory, at any depth. Directories themselves
   (also empty ones), time stamps and permissions do not count.
2. For each file build one record:
   the relative path in POSIX notation (`/` as separator, no leading `./`)
   encoded as UTF-8, one NUL byte, the SHA-256 of the file content as 64
   lower-case hexadecimal characters, one LF byte.
3. Sort the records by the bytes of the path.
4. `tree_sha256` is the SHA-256 of the concatenated records, as 64 lower-case
   hexadecimal characters.

Symbolic links are never followed. A link counts as a file whose content is
the link target as UTF-8 text, so the result is the same whether an extractor
creates real links or writes them as small text files. The checksum of an
empty directory is the SHA-256 of empty input. A subdirectory that cannot be
read is an error (`OSError`); it is never left out silently.

The function is `manifest_tools.tree_sha256(directory)`;
`manifest_tools.file_sha256(path)` gives the checksum of a single file.

## Using the module

```python
from testfactory import manifest_tools

manifest = manifest_tools.load_manifest("testfactory/manifest.yaml")
for entry in manifest.entries:
    print(entry.id, entry.kind, manifest_tools.target_path("testfactory/manifest.yaml", manifest, entry))
```

`load_manifest` and `parse_manifest` raise `ManifestError`; its `problems`
list names entry, field and message of every finding. `Manifest`, `Entry` and
`Terms` are frozen data classes; use `dataclasses.replace` to change a value
and `write_manifest` to store the result.

Code that writes to a target calls
`manifest_tools.checked_target_path(root_dir, entry.target)` first
(`root_dir` from `manifest_tools.root_path(manifest_path, manifest)`). It
raises `UnsafePathError` if any existing part of the path below the root is a
symbolic link or if the resolved path does not lie below the resolved root.
