.PHONY: install run up test build
install:        ; python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt pytest httpx
run:            ; . .venv/bin/activate && uvicorn api.main:app --reload --port 8000
up:             ; docker compose up --build
test:           ; . .venv/bin/activate && pytest
build:          ; docker build -t corvo-prpo .
