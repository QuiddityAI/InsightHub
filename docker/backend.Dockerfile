FROM --platform=$BUILDPLATFORM python:3.11 AS python_env

# install UV python package manager:
COPY --from=ghcr.io/astral-sh/uv:0.6.10 /uv /uvx /bin/

RUN useradd -ms /bin/bash appuser
WORKDIR /app
RUN chown -R appuser /app

# setup python environment and install packages:
COPY pyproject.toml uv.lock README.md /app/
RUN uv sync --frozen

# copy source code:
COPY .env credentials.json /app/
COPY backend /app/backend

FROM python_env as backend

HEALTHCHECK --interval=30s --timeout=3s \
  CMD curl -f http://localhost:55125/org/data_map/health || exit 1

EXPOSE 55125
USER appuser
WORKDIR /app/backend
ENTRYPOINT ["uv", "run"]
CMD ["manage.py", "runserver", "--insecure", "0.0.0.0:55125"]
