FROM --platform=$BUILDPLATFORM nvidia/cuda:12.2.0-runtime-ubuntu22.04 AS cuda_python_env
RUN apt update
RUN apt-get install -y python3-pip
RUN pip install --upgrade pip wheel
RUN pip install pipenv
RUN useradd -ms /bin/bash appuser
WORKDIR /app
COPY Pipfile /app
COPY Pipfile.lock /app
RUN pipenv requirements > requirements.txt \
    && pip install --no-cache-dir -r requirements.txt
RUN chown -R appuser /app
RUN mkdir -p /home/appuser/.cache/huggingface
RUN chmod -R a+rw /home/appuser/.cache/huggingface

FROM cuda_python_env as model_server
EXPOSE 55180
USER appuser
WORKDIR /source_code/model_server
ENTRYPOINT ["python3"]
CMD ["model_server.py"]
