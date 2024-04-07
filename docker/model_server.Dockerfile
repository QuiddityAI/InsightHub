FROM --platform=$BUILDPLATFORM nvidia/cuda:12.0.0-runtime-ubuntu22.04 AS cuda_python_env
RUN apt update
RUN apt install -y software-properties-common
RUN add-apt-repository -y ppa:deadsnakes/ppa && apt update
# to prevent tzdata installation from asking questions:
ARG DEBIAN_FRONTEND=noninteractive
RUN apt install -y python3.11 python3.11-dev python3-pip
RUN apt install -y python3.11-venv
ENV VIRTUAL_ENV=/opt/venv
RUN python3.11 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN pip install --upgrade pip wheel
RUN pip install pipenv
RUN useradd -ms /bin/bash appuser
WORKDIR /app
COPY docker/docker_container_base_python_packages.txt /app
RUN pip install --no-cache-dir -r docker_container_base_python_packages.txt
COPY Pipfile /app
COPY Pipfile.lock /app
RUN apt install -y git  # needed to install pip dependencies from git repos
RUN pipenv requirements > requirements.txt \
    && pip install --no-cache-dir -r requirements.txt
RUN chown -R appuser /app
RUN mkdir -p /home/appuser/.cache/huggingface
RUN chmod -R a+rw /home/appuser/.cache
RUN apt install -y curl

FROM cuda_python_env as model_server

HEALTHCHECK --interval=30s --timeout=3s \
  CMD curl -f http://localhost:55180/health || exit 1

EXPOSE 55180
USER appuser
WORKDIR /source_code/model_server
ENTRYPOINT ["python3.11"]
CMD ["model_server.py"]
