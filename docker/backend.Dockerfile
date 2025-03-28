FROM --platform=$BUILDPLATFORM python:3.11 AS python_env

# install UV python package manager:
COPY --from=ghcr.io/astral-sh/uv:0.6.10 /uv /uvx /bin/

RUN useradd -ms /bin/bash appuser
WORKDIR /app
RUN chown -R appuser /app
RUN mkdir -p /data && chown -R appuser /data
RUN mkdir -p /data/quiddity_data && chown -R appuser /data/quiddity_data

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
# run migrations, import base objects, create Django superuser using environment variables and start app:
ENTRYPOINT ["sh", "-c"]
CMD ["uv run manage.py migrate && uv run manage.py update_base_models && uv run manage.py createsuperuser --noinput || true && uv run manage.py runserver --insecure 0.0.0.0:55125"]
