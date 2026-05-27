#!/bin/bash

# Usage:
#   bash scripts/create_domain.sh "" ability
#   bash scripts/create_domain.sh "/pokemon" ability

set -e

PATH_ARG=$1
NAME_ARG=$2
FILES=(__init__ repository service schema route)

if [ -z "$NAME_ARG" ]; then
  echo "Error: name is required. Usage: make domain name=ability [path=/pokemon]"
  exit 1
fi

DOMAIN_PATH=${PATH_ARG#/}
if [ -n "$DOMAIN_PATH" ]; then
  DOMAIN_RELATIVE_PATH="$DOMAIN_PATH/$NAME_ARG"
else
  DOMAIN_RELATIVE_PATH="$NAME_ARG"
fi

DOMAIN_ENTITY=$NAME_ARG
DOMAIN_MODULE=${DOMAIN_RELATIVE_PATH//\//.}
CLASS_SEED=$NAME_ARG

CLASS_NAME=$(echo "$CLASS_SEED" | awk -F'[_-]' '{for (i=1; i<=NF; i++) printf toupper(substr($i,1,1)) tolower(substr($i,2)); print ""}')

TARGET="app/domain/$DOMAIN_RELATIVE_PATH"

if [ -d "$TARGET" ]; then
  echo "Error: domain '$DOMAIN_RELATIVE_PATH' already exists at $TARGET"
  exit 1
fi

for FILE in "${FILES[@]}"; do
  TEMPLATE="scripts/templates/$FILE.py"
  if [ ! -f "$TEMPLATE" ]; then
    echo "Error: template '$TEMPLATE' not found"
    exit 1
  fi
done

mkdir -p "$TARGET"

cleanup_on_error() {
  if [ -d "$TARGET" ]; then
    rm -rf "$TARGET"
  fi
}

trap cleanup_on_error ERR

for FILE in "${FILES[@]}"; do
  sed \
    -e "s/__DOMAIN_MODULE__/$DOMAIN_MODULE/g" \
    -e "s/__DOMAIN_ENTITY__/$DOMAIN_ENTITY/g" \
    -e "s/__CLASS_NAME__/$CLASS_NAME/g" \
    "scripts/templates/$FILE.py" > "$TARGET/$FILE.py"
done

trap - ERR

echo "✅ Domain '$DOMAIN_RELATIVE_PATH' created at $TARGET"
echo "   → $TARGET/__init__.py"
echo "   → $TARGET/repository.py"
echo "   → $TARGET/service.py"
echo "   → $TARGET/schema.py"
echo "   → $TARGET/route.py"
echo ""
echo "⚠️  Lembre-se de:"
echo "   1. Registrar o router em app/main.py"
echo "   2. Criar o model em app/models/$DOMAIN_ENTITY.py"
echo "   3. Registrar o model em app/models/__init__.py"
echo "   4. Gerar a migration: make create-migration message='add $DOMAIN_ENTITY'"
