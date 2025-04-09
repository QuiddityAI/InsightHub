FROM --platform=$BUILDPLATFORM python:3.11 AS python_env
RUN useradd -ms /bin/bash appuser
WORKDIR /app
RUN chown -R appuser /app
RUN mkdir -p /data && chown -R appuser /data
RUN mkdir -p /data/quiddity_data && chown -R appuser /data/quiddity_data

# install system dependencies:
RUN apt-get update && apt-get install -y build-essential python3-dev \
libldap2-dev libsasl2-dev slapd ldap-utils

FROM python_env as backend

HEALTHCHECK --interval=30s --timeout=3s \
  CMD curl -f http://localhost:55125/org/data_map/health || exit 1

EXPOSE 55125
USER appuser
WORKDIR /source_code/backend
# using virtual env of host for now to make it easier to update packages:
ENTRYPOINT ["bash", "/source_code/dev_startup.sh"]