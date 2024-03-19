# Visual Data Map - Project Title "Quiddity"

This is a Python-backend, Vue-frontend tool to visualize, search, organize and extract data.

Main features:
- ingest data, convert it to embeddings and index it automatically
- generate visual maps of data
- create collections of data, use them to recommend more items using active learning
- create tables of data and extract information from each item using LLMs
- chat with the data and answer questions

-> a "funnel" from massive data amounts to a curated set of items with extracted information

## Development Setup

Currently, the docker containers in this repo are configured for a development setup, i.e. they mount this source folder into the container and have live reload enabled. This means that running `docker compose up -d` should ideally be enough to run the code, modify it and see changes immediately.

This also means that the current docker containers are not meant for production use, due to hot reload they are slow and insecure.

### Steps

Local setup, mostly for IDE auto-complete (but might be needed for Docker containers, too, at the moment, because they mount the source folder):
```
python3.11 -m pip install pipenv
python3.11 -m pipenv install
python3 -m spacy download en_core_web_sm  # not sure if this is still needed

cd frontend/visual-data-map
npm install
```

- install docker >= v24.0 (and nvidia-docker if an Nvidia GPU is available, test the GPU setup with a simple container)
- By default, the docker setup uses `/data/quiddity_data` as a folder to store app data. Make sure it exists or change the mounting point in the docker-compose.yaml file to something else.
- If no Nvidia GPU is available, remove the `deploy:` part about the GPU from the docker-compose file. The code _should_ work without a GPU, too.
- Make sure the env variables and credential files described in `required_environment_variables.txt` exist
- Copy an existing `db.sqlite3` file to the `organization_backend` folder if available, to not start from zero.
  - Otherwise, run `python manage.py migrate` in the `organization_backend` folder to create a database.
  - And `python manage.py createsuperuser` to create the first user
- Run `python manage.py collectstatic` in the `organization_backend` folder
- Make sure the `umap_with_progress_callback-add_progress_callback_0.5.3.zip` file exists in the repo root folder (its used in the data-backend Docker file), otherwise get it [here](https://github.com/luminosuslight/umap_with_progress_callback/archive/refs/heads/add_progress_callback_0.5.3.zip)
- (optionally) Set up VSCode by installing recommended extensions in `vsc-extensions.txt` (can be installed using `VSC Export & Import` extensions, but should be done carefully)
- run `docker compose up -d`

### Testing the setup

- the main frontend should be available at `localhost:55140`
- the OpenSearch admin should be available at `localhost:5601`
- check the docker logs manually for errors or install a tool to easily monitor the logs like `Dozzle`

## Development Notes

- The main structure and the level of high or low 'abstraction' is hopefully quite thought-through and should enable fast development, easy maintanability and high scalability where needed.
- Everything else is quite rudimental and the code is not very clean in many parts, just being there as a proof-of-concept.
  - Please change and improve wherever needed!
  - And especially before we have any customers, make breaking changes and rename stuff as much as needed to improve the code quickly.
- Parts that need to be improved the most (especially before any public deployment):
  - [ ] Authentication + Security: the data-backend code doesn't use any authentication at all yet, the organization-backend only partially. Some ports are exposed without authentication / hardening. HTTPS proxy is missing.
  - [ ] User registration: currently, no e-mail verification is set up and access rights are not really managed.
  - [ ] docker files and docker compose setup (maybe create different ones for production and development, improve time to update dependencies)
  - [ ] Make sure computation power and OpenAI credits are used responsibly: currently, you could accidentially create millions of embeddings, using all of the CPU for ages, and you could also extract information from millions of items using the ChatGPT API -> we need to implement some sort of limits and / or display how much an action costs / needs CPU.
  - [ ] switch from sqlite to Postgres for the organization backend
- Other main TODOs:
  - [ ] De-duplicate and simplify code to generate missing fields of items
  - [ ] allow to export and import Dataset definitions from the Django admin page
  - [ ] replace pipenv with a faster dependency manager
  - [ ] Use a proper third party ML model server instead of the custom one / Infinity (at the moment, using different models simultaniously might fill up the memory and crash, and performance + scalability can also be improved with a third party model server)
  - [ ] move these TODOs to an issue tracker
  - ...
