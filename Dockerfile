# Use Python 3.11 Lite
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first (for caching)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Environment variables
ENV PYTHONUNBUFFERED=1

# Expose the port
EXPOSE 5001

# Run the application
WORKDIR /app/backend
CMD ["python", "app.py"]

