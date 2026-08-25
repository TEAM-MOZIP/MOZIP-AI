# syntax=docker/dockerfile:1

FROM python:3.12-slim

WORKDIR /app

# Docker Compose healthcheck가 사용하는 curl은 이 이미지에 기본 포함되어 있지 않아 명시적으로 설치한다.
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.12.1 /uv /uvx /usr/local/bin/

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY app app

EXPOSE 8000

# uv run이 아니라 venv의 uvicorn을 직접 실행한다 — uv run은 실행 시마다 암묵적으로
# 재동기화를 시도해 --no-dev로 제외한 dev 그룹(ruff 등)을 컨테이너 기동 시 다시
# 네트워크로 내려받는 문제가 실측 확인됐다. 빌드 시 이미 --frozen --no-dev로 만든
# venv를 그대로 쓰면 이 문제가 없다.
CMD [".venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--http", "h11"]
