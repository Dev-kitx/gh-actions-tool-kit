setup-env:
	@echo "🧪 Setting up development environment..."
	uv sync --extra dev
	@echo "✅ Environment ready."

run-pytest:
	@echo "🧪 Running unit tests..."
	uv run pytest --cov-report xml:coverage.xml --cov=. --cov-report=term-missing tests --junitxml=report.xml
	@echo "✅ Unit tests completed."

run-mypy:
	@echo "🔍 Running type checks..."
	uv run mypy actions_tool_kit/
	@echo "✅ Type checks passed."
