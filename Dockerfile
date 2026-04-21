# syntax=docker/dockerfile:1.7

# Small runtime image for the `xiao` CLI. Primarily useful for running
# vacuum commands (status, start, stop, schedule, …) against an existing
# config. `xiao setup browser-login` needs a display and is not meant to
# run in this image — run it once on your workstation and mount the
# resulting config dir into the container.
#
# Build:   docker build -t xiao .
# Run:     docker run --rm -v "$HOME/.config/xiao:/root/.config/xiao" xiao status
#
# Multi-stage: builder has gcc for compiling sdists (netifaces has no
# py3.12 wheels), runtime is slim with only the venv copied in.

ARG WITH_PLAYWRIGHT=0

FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:${PATH}"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential gcc python3-dev libffi-dev \
    && rm -rf /var/lib/apt/lists/* \
    && python -m venv /opt/venv \
    && pip install --upgrade pip \
    && pip install xiao-cli


FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:${PATH}" \
    XDG_CONFIG_HOME=/root/.config

COPY --from=builder /opt/venv /opt/venv

# Playwright browsers are skipped by default (~200 MB vs ~1.5 GB with
# Chromium). Rebuild with `--build-arg WITH_PLAYWRIGHT=1` to include
# Chromium + system deps; not useful here since `xiao setup
# browser-login` needs a display anyway.
ARG WITH_PLAYWRIGHT
RUN if [ "$WITH_PLAYWRIGHT" = "1" ]; then \
        python -m playwright install --with-deps chromium ; \
    fi \
    && mkdir -p /root/.config/xiao

WORKDIR /root

ENTRYPOINT ["xiao"]
CMD ["--help"]
