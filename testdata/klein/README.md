# Small test documents

This folder holds a few small documents for the automatic tests, so that the
tests and the CI do not depend on downloads from third parties.

**Only material under an explicitly free license or in the public domain may
be placed here.** Vendor documents without such a license never go into the
repository. Every file has an entry in [`manifest.yaml`](manifest.yaml) with
origin, version, checksum, size and terms of use (format: see
[`testfactory/README.md`](../../testfactory/README.md)); license texts lie next
to the files. Images and logos are not taken over.

## Files

| Path | Content | Language | License | Origin |
| --- | --- | --- | --- | --- |
| `opnsense/LICENSE` | License of the OPNsense documentation, unchanged | en | BSD-2-Clause | `LICENSE` of [opnsense/docs](https://github.com/opnsense/docs) |
| `opnsense/source/backups.rst` | Configuration: backup, defaults, history | en | BSD-2-Clause | `source/manual/backups.rst` |
| `opnsense/source/updates.rst` | Updates | en | BSD-2-Clause | `source/manual/updates.rst` |
| `opnsense/source/sftp-backup.rst` | Backups via secure copy (sftp) | en | BSD-2-Clause | `source/manual/sftp-backup.rst` |
| `opnsense/source/firewall_groups.rst` | Interface groups | en | BSD-2-Clause | `source/manual/firewall_groups.rst` |
| `opnsense/markdown/*.md` | Markdown versions of the four pages above | en | BSD-2-Clause | generated, see below |
| `recht/BetrSichV.pdf` | Betriebssicherheitsverordnung (60 pages) | de | public domain (official work, § 5 (1) UrhG) | [gesetze-im-internet.de](https://www.gesetze-im-internet.de/betrsichv_2015/) |

### OPNsense documentation

- Repository `https://github.com/opnsense/docs`, branch `master`, commit
  `953dd3d1d1dd2739a18d0b6df5c936146153aff6` (checked in work order 103).
- Copyright Deciso B.V. and the contributors named in `opnsense/LICENSE`;
  2-clause BSD license. The `.rst` files and `LICENSE` are byte-identical
  copies of the raw files at that commit. Only pages without image directives
  were chosen.

### Betriebssicherheitsverordnung

- The only PDF linked from the overview page
  `https://www.gesetze-im-internet.de/betrsichv_2015/`, downloaded on
  2026-11-21 from `https://www.gesetze-im-internet.de/betrsichv_2015/BetrSichV.pdf`,
  file unchanged. Version: last amended by Art. 27 of the act of 18.12.2025
  (BGBl. 2025 I Nr. 347).
- Ordinances are official works without copyright protection,
  § 5 (1) UrhG (`https://www.gesetze-im-internet.de/urhg/__5.html`). The text
  on the portal is the non-official consolidated version.

## How the Markdown versions were made

The reStructuredText pages were converted once with pandoc 3.14
(GPL-2.0-or-later) from the pandoc project's image `pandoc/core` on Docker
Hub, pinned by tag and digest, in a throw-away container without network. pandoc is only used; it is
not part of this project and not part of any project image. The Markdown files
are kept exactly as pandoc writes them, so running a command again gives the
same checksum.

Run from the repository root (POSIX shell or PowerShell):

```sh
docker run --rm --network none -v "${PWD}/testdata/klein/opnsense:/data" -w /data pandoc/core:3.14.0.0@sha256:f6c6e92d8b150cc1e106e0fbdf2697dea179c737c99c8dbf36caa907b7ba7e73 --from=rst --to=gfm --wrap=none --output=markdown/backups.md source/backups.rst
docker run --rm --network none -v "${PWD}/testdata/klein/opnsense:/data" -w /data pandoc/core:3.14.0.0@sha256:f6c6e92d8b150cc1e106e0fbdf2697dea179c737c99c8dbf36caa907b7ba7e73 --from=rst --to=gfm --wrap=none --output=markdown/updates.md source/updates.rst
docker run --rm --network none -v "${PWD}/testdata/klein/opnsense:/data" -w /data pandoc/core:3.14.0.0@sha256:f6c6e92d8b150cc1e106e0fbdf2697dea179c737c99c8dbf36caa907b7ba7e73 --from=rst --to=gfm --wrap=none --output=markdown/sftp-backup.md source/sftp-backup.rst
docker run --rm --network none -v "${PWD}/testdata/klein/opnsense:/data" -w /data pandoc/core:3.14.0.0@sha256:f6c6e92d8b150cc1e106e0fbdf2697dea179c737c99c8dbf36caa907b7ba7e73 --from=rst --to=gfm --wrap=none --output=markdown/firewall_groups.md source/firewall_groups.rst
```

The same command stands in the field `generated_by` of each Markdown entry in
the manifest.

## Checks

With `TF` standing for `docker compose -f deploy/compose/testfactory.yaml`:

```sh
TF run --rm fetch python -m testfactory.manifest_tools check --complete testdata/klein/manifest.yaml
TF run --rm check python -m unittest testfactory.tests.test_testdata_klein -v
```

The test checks the checksums and sizes, that every file in this folder is
listed (except `README.md`, `LICENSE` and `manifest.yaml`), that every entry
allows redistribution under `BSD-2-Clause` or `public-domain`, that every
Markdown version names its origin and command, and that the folder stays below
2 MB.
