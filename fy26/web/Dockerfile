# Image for the course website. web/publish.py stages the build context in web/build/
# (this file, the harness, the website code and the published pages), then runs:
#   az acr build --registry <acr_name> --image lectures:<tag> web/build

FROM ghcr.io/astral-sh/uv:0.11.7 AS uv

FROM python:3.12-slim AS build
COPY --from=uv /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv
WORKDIR /src
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

FROM python:3.12-slim
RUN useradd --system --uid 10001 --no-create-home web
COPY --from=build /opt/venv /opt/venv
WORKDIR /srv
COPY harness ./harness
COPY web ./web
COPY site ./site
ENV PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    LECTURES_SITE_DIR=/srv/site
USER 10001
EXPOSE 8000
# One worker on purpose: harness runs are kept in this process's memory.
CMD ["uvicorn", "--factory", "web.main:create_app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-server-header", "--proxy-headers", "--forwarded-allow-ips", "*"]
