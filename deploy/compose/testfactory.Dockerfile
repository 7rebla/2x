# Check image of the test factory: the same official Python image as the
# `fetch` service in testfactory.yaml (same tag, same digest). Nothing from
# the repository is copied in; the repository is mounted at /work.
FROM python:3.14.10-slim-trixie@sha256:9aaa474097d094040649f2162a627c0049b408f52138d980916788d80f04802f

# The type checker (mypy, fixed version) is installed here once the licenses
# of its dependencies are approved; see work order 101.

WORKDIR /work
