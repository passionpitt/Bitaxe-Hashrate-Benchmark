# Use Python 3.10.12 slim image as base
FROM python:3.10.12-slim

# Set working directory
WORKDIR /app

COPY . .

# Install dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r src/requirements.txt

# Set the entrypoint
ENTRYPOINT ["python", "bitaxe_hashrate_benchmark.py"]
