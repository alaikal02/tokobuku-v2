# Dockerfile for tokobuku-v2 (Darussholah Publisher & Retailer)
FROM python:3.11-alpine

WORKDIR /app

# Copy all static assets, backend server, and initial data
COPY . /app

# Ensure uploads directory exists
RUN mkdir -p /app/uploads

EXPOSE 8000

CMD ["python3", "server.py", "8000"]
