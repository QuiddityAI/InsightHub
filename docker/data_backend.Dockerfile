FROM --platform=$BUILDPLATFORM python:3.11 AS python_env
RUN pip install pipenv
RUN useradd -ms /bin/bash appuser
WORKDIR /app
COPY docker/docker_container_base_python_packages.txt /app
RUN pip install --no-cache-dir -r docker_container_base_python_packages.txt
COPY Pipfile /app
COPY Pipfile.lock /app
RUN pipenv requirements > requirements.txt \
    && pip install --no-cache-dir -r requirements.txt
RUN chown -R appuser /app

FROM python_env as data_backend
EXPOSE 55123

RUN pip uninstall -y umap-learn
# RUN wget "https://github.com/luminosuslight/umap_with_progress_callback/archive/refs/heads/add_progress_callback_0.5.3.zip"
COPY umap_with_progress_callback-add_progress_callback_0.5.3.zip /app
RUN unzip umap_with_progress_callback-add_progress_callback_0.5.3.zip
RUN rm umap_with_progress_callback-add_progress_callback_0.5.3.zip
RUN cd "umap_with_progress_callback-add_progress_callback_0.5.3" && python setup.py install && cd ..

USER appuser
WORKDIR /source_code/data_backend
ENTRYPOINT ["python3"]
CMD ["backend_server.py"]
