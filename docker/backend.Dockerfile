FROM --platform=$BUILDPLATFORM python:3.11 AS python_env
RUN pip install pipenv
RUN useradd -ms /bin/bash appuser
WORKDIR /app
RUN chown -R appuser /app

FROM python_env as backend

HEALTHCHECK --interval=30s --timeout=3s \
  CMD curl -f http://localhost:55125/org/data_map/health || exit 1

EXPOSE 55125
USER appuser
WORKDIR /source_code/backend
# using virtual env of host for now to make it easier to update packages:
ENTRYPOINT ["/source_code/.venv/bin/python3"]
CMD ["manage.py", "runserver", "--insecure", "0.0.0.0:55125"]
