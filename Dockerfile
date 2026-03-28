FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY aggregator.py .

# Set environment
ENV PYTHONUNBUFFERED=1

# Run aggregator with scheduler
CMD ["python", "aggregator.py"]
