# Updating the Servers

## Notes

- docker compose down
- on v2: source start_ssh_agent.sh
- git stash
- checkout git
- git stash pop (& fix merging problems)
- update .env file
- update npm env in frontend/? (not needed if npm install is in RUN command of container, July 2024)
- rebuild / update docker containers? (was not needed July 2024)
  - poetry install
  - update qdrant:
  - docker compose pull qdrant
  - docker compose up --force-recreate --build -d qdrant
- docker compose up -d postgres organization-backend
- apply migrations?
  - Attention: on v2, there is a different postgres running on same port, migrations must be done in container!
  - from within container:
  - docker exec -it visual-data-map-organization-backend-1 bash
  - ../.venv/bin/python manage.py migrate
  - ../.venv/bin/python manage.py update_base_models
- docker compose restart organization-backend
- docker compose up -d
- wait, especially till webserver-prod has run npm install and compiled the website
- make sure generators have embedding space set (migration after changing id from int to str doesn't work here)
- make sure datasets have correct schema assigned
- make sure schemas have import converters set (import doesn't yet work apparently)
- make sure orgs have applicable schemas set, and default datasets

