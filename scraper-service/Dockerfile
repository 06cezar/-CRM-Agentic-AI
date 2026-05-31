FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Virtual framebuffer so we can run a real headful Firefox (more authentic
# fingerprint than headless) without a physical display.
RUN apt-get update && apt-get install -y --no-install-recommends xvfb \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m playwright install firefox

COPY . .

EXPOSE 8002

# Run uvicorn under Xvfb; screen size matches the browser viewport.
# Shell form so the --server-args quoting is parsed correctly (the exec-form
# "-s", "-screen ..." split makes xvfb-run swallow the command as its own args).
CMD xvfb-run -a --server-args="-screen 0 1440x900x24" uvicorn main:app --host 0.0.0.0 --port 8002
