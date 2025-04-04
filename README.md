# Quiddity InsightHub

This is a Python-Django-backend, Vue-frontend tool to visualize, search, organize and extract data.

Main features:
- ingest data, convert it to embeddings and index it automatically
- generate visual maps of data
- create collections of data, use them to recommend more items using active learning
- create tables of data and extract information from each item using LLMs
- chat with the data and answer questions

-> a "funnel" from massive data amounts to a curated set of items with extracted information

## Status and Security

**Status:** The InsightHub works and when configured correctly, it can provide value in a real life setting.
But the project and codebase is still in alpha stage, i.e. not everything is properly documented, some features might not work as expected or are not even implemented.

**Maintenance:** The project is not maintened actively at the moment. Let us know if you are interested in maintaining it or paying for maintenance.

**Security:** Currently, the system is not meant for production use. There are several major security issues with the current set up, e.g. using the vite and Django development webservers instead of a production server like gunicorn. Even though the databases are not exposed to the outside, the connections should not use default passwords as currently. Lastly, the API does not use authentication for every endpoint yet, and even the endpoints that use it are not tested for security.

In total, the project can provide value e.g. in a controlled environment like an intranet, and many issues can be solved rather easily, but it should not be used exposed to the internet and with confidential data at the moment.

## Running the system

- install docker >= v24.0 (and nvidia-docker if an Nvidia GPU is available, test the GPU setup with a simple container)
- check out the git repository
- create a `.env` file according to the variables listed in [required_environment_variables.txt](required_environment_variables.txt)
- add `docker-compose.override.pdferret.yaml` to your `COMPOSE_FILE` env variable (colon separated) if you want to be able to upload and parse PDF files (and other documents)
- run `docker compose up -d`
- go to `localhost:55140` and log in with e-mail `admin@example.com` and password `admin` (if not changed using env variables)
- visit the admin interface using the top right user menu and the "database" icon for more settings

### Updating the system

Not tested yet, but should work like this:

- `git pull`
- `docker compose down backend webserver`
- `docker compose up -d --build backend`
- `docker compose up -d --build webserver`

## Further Setup Configuration

- Data storage: By default, a docker volumes are used to store data like uploaded files and the database content. Override the docker volume setup to change this.
- GPU: The system can work without a GPU. If an Nvidia GPU is available, add `docker-compose.override.gpu.yaml` to your COMPOSE_FILE env variable (with a : after the other docker compose files). It enables GPU support for the containers to e.g. generate embeddings or maps using the GPU.
- To use Google LLMs, create a credentials file before building the Docker container using: `gcloud auth application-default login`, it will then be mounted to the container.

## Development Setup

Using the `docker-compose.override.dev.yaml` file, you get containers that are configured for a development setup, i.e. they mount this source folder into the container and have live reload enabled. This means that running `docker compose up -d` should ideally be enough to run the code, modify it and see changes immediately.

- If you want to hot-reload the front- and backend code, add `docker-compose.override.dev.yaml` to your COMPOSE_FILE env variable (with a : after the main docker compose file)
- (optionally) Set up VSCode by installing recommended extensions in `vsc-extensions.txt` (can be installed using `VSC Export & Import` extensions, but should be done carefully)

### Pre-commit

pre-commit usage is recommended. To install it run `pip install pre-commit` and then `pre-commit install`. This will ensure continuity of the code formatting.

## Development Notes

- The main structure and the level of high or low 'abstraction' is hopefully quite thought-through and should enable fast development, easy maintanability and high scalability where needed.
- Everything else is quite rudimental and the code is not very clean in many parts, just being there as a proof-of-concept.
  - Please change and improve wherever needed!
- Parts that need to be improved the most (especially before any public deployment):
  - [ ] User registration: currently, no e-mail verification is set up and access rights are not really managed.
  - many more...
