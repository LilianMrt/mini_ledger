#!/bin/bash
set -e
source ../.venv/bin/activate
sudo systemctl start docker
docker compose up -d

docker compose exec postgres sh -c 'until pg_isready -U mini_ledger_user -d mini_ledger_db; do sleep 1; done'

if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
else
    echo "Error: .env not found"
    exit 1
fi

python3 initialization/init_db.py --with-mock

docker exec -it $(docker compose ps -q postgres) psql -U $DB_USER -d $DB_NAME -c "\dt"