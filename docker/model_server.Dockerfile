FROM --platform=$BUILDPLATFORM nvidia/cuda:12.0.0-runtime-ubuntu22.04 AS cuda_python_env
RUN apt update && apt install -y software-properties-common
RUN add-apt-repository -y ppa:deadsnakes/ppa && apt update
# to prevent tzdata installation from asking questions:
ARG DEBIAN_FRONTEND=noninteractive
RUN apt update && apt install -y python3.11 python3.11-dev python3-pip curl git
RUN curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR="/usr/bin" sh
ENV VIRTUAL_ENV=/opt/venv
RUN uv venv --python-preference=only-system $VIRTUAL_ENV --python 3.11
RUN uv pip install --upgrade pip wheel
RUN useradd -ms /bin/bash appuser
WORKDIR /app
COPY docker/model_server_requirements.txt /app
RUN uv pip install --no-cache-dir -r model_server_requirements.txt
RUN chown -R appuser /app
RUN mkdir -p /home/appuser/.cache/huggingface
RUN chmod -R a+rw /home/appuser/.cache
ENV PATH="/opt/venv/bin:$PATH"
FROM cuda_python_env as model_server

HEALTHCHECK --interval=30s --timeout=3s \
  CMD curl -f http://localhost:55180/health || exit 1

EXPOSE 55180
USER appuser
WORKDIR /source_code/model_server
ENTRYPOINT ["python3.11"]
CMD ["model_server.py"]
