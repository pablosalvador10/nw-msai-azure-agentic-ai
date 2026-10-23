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

# Mermaid draws the diagrams in course Markdown. One pinned file, checked against its SHA-256.
FROM python:3.12-slim AS vendor
RUN python -c "import hashlib, sys, urllib.request; \
    url = 'https://cdn.jsdelivr.net/npm/mermaid@12.2.0/dist/mermaid.min.js'; \
    data = urllib.request.urlopen(url, timeout=120).read(); \
    digest = hashlib.sha256(data).hexdigest(); \
    ok = digest == 'a8a6a6f805b074a8261a2825c86f99c8054acb3b35f50bb7e24a4f9f2c3c3b9f'; \
    sys.exit('mermaid checksum mismatch: ' + digest) if not ok else open('/mermaid.min.js', 'wb').write(data)"

FROM python:3.12-slim
RUN useradd --system --uid 10001 --no-create-home web
COPY --from=build /opt/venv /opt/venv
WORKDIR /srv
COPY harness ./harness
COPY web ./web
COPY site ./site
COPY --from=vendor /mermaid.min.js ./web/static/vendor/mermaid-12.2.0.min.js
ENV PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    LECTURES_SITE_DIR=/srv/site
USER 10001
EXPOSE 8000
# One worker on purpose: harness runs are kept in this process's memory.
CMD ["uvicorn", "--factory", "web.main:create_app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-server-header", "--proxy-headers", "--forwarded-allow-ips", "*"]
