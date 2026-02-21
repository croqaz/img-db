FROM ghcr.io/astral-sh/uv:debian
WORKDIR /app
COPY imgdb /app/imgdb
COPY README.md pyproject.toml uv.lock /app/
RUN ["uv", "sync"]
ENTRYPOINT ["uv", "run", "imgdb"]
