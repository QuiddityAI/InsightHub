# visual-data-map
An interactive map to visualise large sets of data embeddings using WebGL

## How it was created initially

- install weaviate using docker-compose
- run `pipenv install` and  `source activate_venv.py`
- create vite app with `cd frontend && npm create vite@latest`
- install tailwind by following this: https://tailwindcss.com/docs/guides/vite

## How to set up on a new machine

```
python3.10 -m pip install pipenv
python3.10 -m pipenv install
python3 -m spacy download en_core_web_sm

cd frontend/visual-data-map
npm install
```

## How to run it

```
# set up port forwardings in local terminal
# frontend:
ssh -L 55140:localhost:55140 home-server

# make sure weaviate is running
cd ../weaviate
docker compose up -d
cd ../visual-data-map

# activate pipenv in each terminal
source activate_venv.py

# model server
python3 model_server.py

# backend server
python3 backend_server.py

# frontend server
cd frontend/visual-data-map
npx vite --port 55140
```

### Change pip temp dir to install large dependencies

`export TMPDIR=$HOME/tmp`


### How Django backend was created:

```
python3 -m pipenv install Django  # version 4.2.2
django-admin startproject project_base
mv project_base django_backend
cd django_backend
python manage.py startapp data_map_backend
python manage.py migrate
python manage.py createsuperuser
sh start_server.py
```
[::]