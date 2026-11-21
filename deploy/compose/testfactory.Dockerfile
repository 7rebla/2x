# Check image of the test factory: the same official Python image as the
# `fetch` service in testfactory.yaml (same tag, same digest). Nothing from
# the repository is copied in; the repository is mounted at /work.
FROM python:3.14.10-slim-trixie@sha256:9aaa474097d094040649f2162a627c0049b408f52138d980916788d80f04802f

# mypy (MIT) with all dependencies pinned. pathspec is MPL-2.0 and
# typing_extensions is PSF-2.0; both are used unmodified as tools only
# (decision E-23 in docs/DECISIONS.md).
RUN pip install --no-cache-dir --disable-pip-version-check --root-user-action=ignore \
        mypy==2.4.1 \
        typing_extensions==4.16.0 \
        mypy_extensions==1.2.0 \
        pathspec==1.1.1 \
        librt==0.17.0 \
        ast-serialize==0.13.1

WORKDIR /work
