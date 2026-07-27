.PHONY: install migrate run test release-check retention-scan retention-apply compose-check docker-build docker-up

install:
	python -m pip install -r requirements.txt

migrate:
	alembic upgrade head

run:
	uvicorn app.main:app --reload

test:
	pytest -q

release-check:
	python scripts/release_check.py

retention-scan:
	python scripts/cleanup_attachments.py

retention-apply:
	python scripts/cleanup_attachments.py --apply

compose-check:
	docker compose config -q

docker-build:
	docker build -t autopassport:mvp .

docker-up:
	docker compose up --build
