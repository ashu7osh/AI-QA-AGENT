# # Microsoft's official Playwright image already has Chromium/Firefox/WebKit
# # and all OS-level dependencies baked in — this is the standard way real
# # teams containerize Playwright tests instead of fighting apt installs.
# FROM mcr.microsoft.com/playwright/python:v1.47.0-jammy

# WORKDIR /app

# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# COPY . .

# # Playwright browsers are already installed in the base image, so no
# # `playwright install` step is needed here.

# ENV PYTHONUNBUFFERED=1

# # Default: run the full pytest suite. Override at `docker run` time, e.g.:
# #   docker run --env-file .env myimage python app.py "Test login" --url https://www.saucedemo.com
# CMD ["pytest", "-m", "smoke"]




FROM mcr.microsoft.com/playwright/python:v1.47.0-jammy

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p logs reports

CMD ["pytest", "-m", "smoke and pom"]
