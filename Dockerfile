FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy project files
COPY pyproject.toml uv.lock ./
COPY weather.py ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Expose port
EXPOSE 8001

# Run the server
CMD ["uv", "run", "weather.py", "--host", "0.0.0.0", "--port", "8001"]
