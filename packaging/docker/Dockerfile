FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        libx11-6 \
        pulseaudio-utils \
        tini \
        xdotool \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md /app/
COPY src /app/src

RUN python -m pip install --upgrade pip \
    && python -m pip install .

ENTRYPOINT ["/usr/bin/tini", "--", "whisper-hotkey"]
CMD ["--version"]
