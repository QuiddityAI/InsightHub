# Installation

## Running the system

- install docker >= v24.0 (and nvidia-docker if an Nvidia GPU is available, test the GPU setup with a simple container)
- check out the git repository 
```console
git clone https://github.com/QuiddityAI/InsightHub.git
cd InsightHub
```
- create a `.env` file according to the variables listed in [required_environment_variables.txt](https://github.com/QuiddityAI/InsightHub/blob/main/required_environment_variables.txt)

```console
cp required_environment_variables.txt .env
```
and edit the `.env` file to set the variables. File specifies which environment variables are required for the system to run. The LLM functionality (handled by [LLMonkey](https://github.com/QuiddityAI/LLMonkey)) uses Mistral models by default, so it's sufficient to only set `LLMONKEY_MISTRAL_API_KEY` env var. See [their manual for details](https://docs.mistral.ai/getting-started/quickstart/).

- add `docker-compose.override.pdferret.yaml` to your `COMPOSE_FILE` env variable (colon separated) if you want to be able to upload and parse PDF files (and other documents)
- run `docker compose up -d`. If your setup requires using docker with `sudo`, run `sudo -E docker compose up -d` instead. This important because docker-compose is mounting HOME directory in the containe to get access to gcloud credentials. If `sudo` is used without `-E`, the HOME directory will be different (`/root`) and the credentials will not be found.
- go to `localhost:55140` and log in with e-mail `admin@example.com` and password `admin` (if not changed using env variables)
- visit the Django admin interface (using the top right user menu and the "database" icon) for more settings

## Things to try after initial installation

- Chat (if you added LLM API keys): create a new empty collection, click on "Summaries" at the top right, type in a question and press enter. You can use it like a classic ChatGPT chat.
- Upload PDF documents (if you added the PDFerret docker container + LLM API keys): click on "upload documents" on the top left -> "My Dataset" -> "+ Choose" to select files -> "Upload". You should then be able to search for those documents in new collections.

### Upload your own data via Upload

You can upload individual files as well as .zip files with multiple files in the user interface.
You can also upload CSV files with multiple entries for some dataset schemas (e.g. scientific documents).

### Upload your own data via API

You can upload individual files or arbitrary JSON documents with your own data using the API.
See the folder [scripts_and_examples/import_scripts](https://github.com/QuiddityAI/InsightHub/tree/main/scripts_and_examples/import_scripts) for examples (some might be outdated, check [import_local_german_files.py](https://github.com/QuiddityAI/InsightHub/blob/main/scripts_and_examples/import_scripts/import_local_german_files.py) first).
