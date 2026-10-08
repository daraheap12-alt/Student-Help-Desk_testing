run:
	uv run streamlit run app.py

dashboard:
	uv run streamlit run dashboard.py

generate-data:
	uv run python generate_data.py --count 25

check-data:
	uv run python -c "from ingest import load_faq_data; docs = load_faq_data(); print(f'{len(docs)} valid FAQ records loaded')"

help:
	@echo "Run: make run"
	@echo "Dashboard: make dashboard"
	@echo "Generate dashboard test records: make generate-data"
	@echo "Validate data: make check-data"
	@echo "Custom query: uv run python assistant.py \"How can I enroll in a course?\""
