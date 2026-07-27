.PHONY: install migrate run test docker-build docker-up

install:
	python -m pip install -r requirements.txt

migrate:
	alembic upgrade head

run:
	uvicorn app.main:app --reload

test:
	pytest -q

compose-check:
	docker compose config -q

docker-build:
	docker build -t autopassport:mvp .

docker-up:
	docker compose up --build
