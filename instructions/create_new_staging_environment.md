# Create new staging environment

```
git clone git@github.com:luminosuslight/visual-data-map.git visual-data-map-showcase
cd visual-data-map-showcase/
python3.11 -m venv .venv
source .venv/bin/activate
# in other folder: pip freeze > requirements.txt
# or even better: tidy up requirements first
pip install -U wheel pip
pip install -r requirements.txt
# or: poetry install

cp ../visual-data-map/.env .
cp ../visual-data-map-staging/credentials.json .

cp ../visual-data-map-staging/docker-compose-staging.override.yaml .
vim ../visual-data-map-staging/.env
# make sure COMPOSE_FILE=docker-compose-showcase.yaml is set

# in docker-compose-staging.yaml:
- change name at the top
- change port of webserver

docker compose up -d

# run migrations
docker compose exec -it backend-showcase bash
../.venv/bin/python manage.py migrate
../.venv/bin/python manage.py update_base_models
../.venv/bin/python manage.py createsuperuser

docker compose restart backend-showcase

# create organization

autossh -R 55441:[::1]:55441 user@v2.absclust.com

```
