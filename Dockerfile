FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app files
COPY app.py kite_data.py scanner_engine.py trendline_engine.py universe.py momentum_scanner.py ./
COPY templates/ templates/
COPY static/ static/

EXPOSE 8888

CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8888"]
