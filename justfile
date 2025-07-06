run:
    uv run main.py

show_db:
    uv run show_db.py

fmt:
    uv run pre-commit run -a

format:
    just fmt

type-check:
    uv run ty check .
