# syntax=docker/dockerfile:1.7

# Small runtime image for the `xiao` CLI. Primarily useful for running
# vacuum commands (status, start, stop, schedule, …) against an existing
# config. `xiao setup browser-login` needs a display and is not meant to
# run in this image — run it once on your workstation and mount the
# resulting config dir into the container.
#
# Build:   docker build -t xiao .
# Run:     docker run --rm -v "$HOME/.config/xiao:/root/.config/xiao" xiao status
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    XDG_CONFIG_HOME=/root/.config

# Playwright runtime deps — skipped by default to keep the image small
# (≈200 MB vs ≈1.5 GB with Chromium). Rebuild with `--build-arg WITH_PLAYWRIGHT=1`
# if you want `xiao setup browser-login` to run from inside the container
# (requires mounting an X display or Xvfb; not covered here).
ARG WITH_PLAYWRIGHT=0

RUN pip install --no-cache-dir xiao-cli \
    && if [ "$WITH_PLAYWRIGHT" = "1" ]; then \
           python -m playwright install --with-deps chromium ; \
       fi \
    && mkdir -p /root/.config/xiao

WORKDIR /root

ENTRYPOINT ["xiao"]
CMD ["--help"]
