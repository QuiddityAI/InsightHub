FROM --platform=$BUILDPLATFORM nvidia/cuda:12.0.0-runtime-ubuntu22.04 AS cuda_python_env_data_backend
RUN apt update
RUN apt install -y software-properties-common
RUN add-apt-repository -y ppa:deadsnakes/ppa && apt update
# to prevent tzdata installation from asking questions:
ARG DEBIAN_FRONTEND=noninteractive
RUN apt install -y python3.11 python3.11-dev python3-pip
RUN apt install -y python3.11-venv
# make /usr/bin/python3 point to /usr/bin/python3.11 (because venv uses /usr/bin/python3)
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

RUN python3.11 -m pip install pipenv
RUN apt update && apt install -y libgl1  # for pdfferret (and there for cv2)
RUN apt update && apt install -y tesseract-ocr tesseract-ocr-eng ghostscript  # for pytesseract in pdferret
RUN useradd -ms /bin/bash appuser
WORKDIR /app
#COPY docker/docker_container_base_python_packages.txt /app
#RUN pip install --no-cache-dir -r docker_container_base_python_packages.txt
#COPY Pipfile /app
#COPY Pipfile.lock /app
#RUN pipenv requirements > requirements.txt \
#    && pip install --no-cache-dir -r requirements.txt
RUN chown -R appuser /app

FROM cuda_python_env_data_backend as data_backend
EXPOSE 55123

#RUN pip uninstall -y umap-learn
# RUN wget "https://github.com/luminosuslight/umap_with_progress_callback/archive/refs/heads/add_progress_callback_0.5.3.zip"
#COPY umap_with_progress_callback-add_progress_callback_0.5.3.zip /app
#RUN unzip umap_with_progress_callback-add_progress_callback_0.5.3.zip
#RUN rm umap_with_progress_callback-add_progress_callback_0.5.3.zip
#RUN cd "umap_with_progress_callback-add_progress_callback_0.5.3" && python setup.py install && cd ..

HEALTHCHECK --interval=30s --timeout=3s \
  CMD curl -f http://localhost:55123/health || exit 1

USER appuser
WORKDIR /source_code/data_backend
# using virtual env of host for now to make it easier to update packages:
ENTRYPOINT ["/source_code/.venv/bin/python3.11"]
CMD ["backend_server.py"]
