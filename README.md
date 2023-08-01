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

cd frontend/visual-data-map
npm install
```

## How to run it

```
# set up port forwardings in local terminal
# backend (accessed from JS in browser):
ssh -L 55123:localhost:55123 home-server
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
