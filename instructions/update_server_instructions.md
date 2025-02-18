# Updating the Servers

## Notes

- docker compose down
- git stash
- git pull
- git stash pop (& fix merging problems)
- update .env file
- update npm env in frontend/? (not needed if npm install is in RUN command of container, July 2024)
- rebuild / update docker containers? (was not needed July 2024)
  - update qdrant:
  - docker compose pull qdrant
  - docker compose up --force-recreate --build -d qdrant
- update virtualenv:
  - uv sync
- docker compose up -d postgres backend
- apply migrations:
  - from within container:
  - docker compose exec -it backend bash
  - docker compose exec -it backend-showcase bash
  - docker compose exec -it backend-staging bash
  - ../.venv/bin/python manage.py migrate
  - ../.venv/bin/python manage.py update_base_models
- docker compose restart backend
- docker compose restart webserver-prod-showcase
- docker compose up -d
- wait, especially till webserver-prod has run npm install and compiled the website
- make sure generators have embedding space set (migration after changing id from int to str doesn't work here)
- make sure datasets have correct schema assigned
- make sure schemas have import converters set (import doesn't yet work apparently)
- make sure orgs have applicable schemas set, and default datasets
