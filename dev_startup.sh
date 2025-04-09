#!/bin/bash
# ldap module must be installed from inside the container
# to make sure it's using correct libraries
/source_code/.venv/bin/python3 -m pip install python-ldap
# run the server
/source_code/.venv/bin/python3 manage.py runserver --insecure 0.0.0.0:55125
