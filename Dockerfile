# Use Python 3.10.12 slim image as base
FROM python:3.10.12-slim

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the script
COPY bitaxe_hashrate_benchmark.py .

# Set the entrypoint
ENTRYPOINT ["python", "bitaxe_hashrate_benchmark.py"]
