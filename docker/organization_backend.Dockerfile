FROM --platform=$BUILDPLATFORM python:3.11 AS python_env
RUN pip install pipenv
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

FROM python_env as organization_backend

HEALTHCHECK --interval=30s --timeout=3s \
  CMD curl -f http://localhost:55125/org/data_map/health || exit 1

EXPOSE 55125
USER appuser
WORKDIR /source_code/organization_backend
# using virtual env of host for now to make it easier to update packages:
ENTRYPOINT ["/source_code/.venv/bin/python3"]
CMD ["manage.py", "runserver", "0.0.0.0:55125"]
