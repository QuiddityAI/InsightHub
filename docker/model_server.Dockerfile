FROM --platform=$BUILDPLATFORM nvidia/cuda:12.2.0-runtime-ubuntu22.04 AS cuda_python_env
RUN apt update
RUN add-apt-repository -y ppa:deadsnakes/ppa && apt update
RUN apt install python3.11
RUN apt-get install -y python3.11-pip
RUN python3.11 -m pip install --upgrade pip wheel
RUN python3.11 -m pip install pipenv
RUN useradd -ms /bin/bash appuser
WORKDIR /app
COPY docker/docker_container_base_python_packages.txt /app
RUN python3.11 -m pip install --no-cache-dir -r docker_container_base_python_packages.txt
COPY Pipfile /app
COPY Pipfile.lock /app
RUN python3.11 -m pipenv requirements > requirements.txt \
    && python3.11 -m pip install --no-cache-dir -r requirements.txt
RUN chown -R appuser /app
RUN mkdir -p /home/appuser/.cache/huggingface
RUN chmod -R a+rw /home/appuser/.cache/huggingface

FROM cuda_python_env as model_server
EXPOSE 55180
USER appuser
WORKDIR /source_code/model_server
ENTRYPOINT ["python3.11"]
CMD ["model_server.py"]
