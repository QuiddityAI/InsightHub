#!/bin/bash

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <python install root>"
    exit 1
fi

# fix the symlink
rm .venv/bin/python3
ln -s /source_code/$1/bin/python .venv/bin/python3

# update .env
VAR_NAME="DOCKER_PYTHONHOME"
VAR_VALUE=/source_code/$1

# Escape special characters for sed
ESCAPED_VALUE=$(printf '%s\n' "$VAR_VALUE" | sed 's/[\/&]/\\&/g')

# Check if the variable exists in .env
if grep -q "^$VAR_NAME=" .env; then
    # Update the existing variable
    sed -i "s/^$VAR_NAME=.*/$VAR_NAME=\"$ESCAPED_VALUE\"/" .env
else
    # Append the new variable
    echo "$VAR_NAME=\"$VAR_VALUE\"" >> .env
fi
