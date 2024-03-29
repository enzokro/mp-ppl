# Stage 1: Build
FROM python:3.10-slim as builder

# Set environment variables to reduce Python package cruft and avoid running as root
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Create a non-root user named 'cck' within a group 'cckgroup'
RUN addgroup --system cckgroup && \
    adduser --system --ingroup cckgroup cck

# Set the working directory in the container to /app
WORKDIR /app

# Install system dependencies required for building Python packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies globally in the container (avoiding the user directory)
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy the Flask application into the container
COPY . .

# Stage 2: Run
FROM python:3.10-slim as runner

# Import the non-root user 'cck' from the builder stage
COPY --from=builder /etc/passwd /etc/group /etc/

# Copy the Python environment and installed packages from the builder stage
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Set the non-root user 'cck' to run the application
USER cck

# Set the working directory and copy the application from the builder stage
WORKDIR /app
COPY --from=builder /app /app

# Healthcheck to ensure the application is running (requires curl installed or use a custom script)
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:6767/ || exit 1

# Run Gunicorn to serve the Flask application
CMD ["gunicorn", "-b", "0.0.0.0:6767", "--access-logfile", "-", "--error-logfile", "-", "app:app"]
