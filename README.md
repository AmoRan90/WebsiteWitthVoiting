# Voting App

Приложение для голосования на FastAPI + PostgreSQL + Docker Swarm.

## Стек
- Python 3.12, FastAPI, SQLAlchemy (async), asyncpg
- PostgreSQL 16
- Docker, Docker Swarm
- Jinja2 (SSR)

## Запуск локально

    docker compose up -d --build

Открыть http://localhost

## Развёртывание в Swarm

    docker stack deploy -c docker-stack.yml voting
