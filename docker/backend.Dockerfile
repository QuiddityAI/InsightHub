FROM --platform=$BUILDPLATFORM python:3.11 AS python_env

# install uv package manager:
COPY --from=ghcr.io/astral-sh/uv:0.6.5 /uv /uvx /bin/

# for django-auth-ldap:
RUN apt update && apt install -y libldap2-dev libsasl2-dev libssl-dev

# setup user and working directory:
RUN useradd -ms /bin/bash appuser
WORKDIR /app
RUN chown -R appuser /app

# copy requirements and install them:
COPY uv.lock /app
COPY pyproject.toml /app
COPY README.md /app
RUN uv sync --frozen

FROM python_env as backend

HEALTHCHECK --interval=30s --timeout=3s \
  CMD curl -f http://localhost:55125/org/data_map/health || exit 1

EXPOSE 55125
USER appuser

# in this development container, the source code is mounted from the host:
WORKDIR /source_code/backend

# we are still using the virtual environment in the container created by uv before:
ENTRYPOINT ["/app/.venv/bin/python3.11"]
CMD ["manage.py", "runserver", "--insecure", "0.0.0.0:55125"]
