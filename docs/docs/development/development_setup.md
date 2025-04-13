# Development Setup

Using the `docker-compose.override.dev.yaml` file, you get containers that are configured for a development setup, i.e. they mount this source folder into the container and have live reload enabled. This means that running `docker compose up -d` should ideally be enough to run the code, modify it and see changes immediately

- If you want to hot-reload the front- and backend code, add `docker-compose.override.dev.yaml` to your COMPOSE_FILE env variable (with a : after the main docker compose file)
- (optionally) Set up VSCode by installing recommended extensions in `vsc-extensions.txt` (can be installed using `VSC Export & Import` extensions, but should be done carefully)

## Backend

Since development setup is using host python environment, you need to install the required packages in your host environment. To do this  

1. Install [uv](https://github.com/astral-sh/uv)
2. Create local install of python in the project root (py3.11 here for example)
`uv python install -i ./ 3.11`. This will create a directory like `cpython-3.11.11-linux-x86_64-gnu` in the project root.
3. Install the required packages using uv:
`uv sync --python cpython-3.11.11-linux-x86_64-gnu` (replace with the name of the directory created in the previous step)
4. run the script `fix-python-install.sh cpython-3.11.11-linux-x86_64-gnu` that will fix the symlinks and update the PYTHONHOME environment to be used inside the docker container. 

This is necessary to set up correctly the host python environment inside the docker container.

 If your setup requires using docker with `sudo`, run `sudo -E docker compose up -d` instead. This important because docker-compose is mounting HOME directory in the containe to get access to gcloud credentials. If `sudo` is used without `-E`, the HOME directory will be different (`/root`) and the credentials will not be found.

### Debugging the backend
The dev setup exposes debugpy on port 30001. You can attach a debugger using Python Debugger: Remote Attach configuration in VSCode. Make sure to correctly set pathMapping, so that VSCode can find the source code in the container. 
```json
...
"pathMappings": [
        {
          "localRoot": "${workspaceFolder}/backend",
          "remoteRoot": "."
        }
      ]
...
```

## Frontend

The idea of mounting host folder is also used for the frontend. It is necessary to install the required packages in the host environment. To do this  

1. Make sure you have nodejs and npm installed on your host machine
2. Install the required packages using npm:
```console
cd frontend
npm install
```


### Pre-commit

pre-commit usage is recommended. To install it run `pip install pre-commit` and then `pre-commit install`. This will ensure continuity of the code formatting.

## Development Notes

- The main structure and the level of high or low 'abstraction' is hopefully quite thought-through and should enable fast development, easy maintanability and high scalability where needed.
- Everything else is quite rudimental and the code is not very clean in many parts, just being there as a proof-of-concept.
  - Please change and improve wherever needed!
- Parts that need to be improved the most (especially before any public deployment):
  - User registration: currently, no e-mail verification is set up and access rights are not really managed.
  - many more...


## Updating the system

Not tested yet, but should work like this:

- `git pull`
- `docker compose down backend webserver`
- `docker compose up -d --build backend`
- `docker compose up -d --build webserver`

## Further Setup Configuration

- Data storage: By default, a docker volumes are used to store data like uploaded files and the database content. Override the docker volume setup to change this.
- GPU: The system can work without a GPU. If an Nvidia GPU is available, add `docker-compose.override.gpu.yaml` to your COMPOSE_FILE env variable (with a : after the other docker compose files). It enables GPU support for the containers to e.g. generate embeddings or maps using the GPU.
- To use Google LLMs, create a credentials file before building the Docker container using: `gcloud auth application-default login`, it will then be mounted to the container.
- see [required_environment_variables.txt](https://github.com/QuiddityAI/InsightHub/blob/main/required_environment_variables.txt) for more settings
