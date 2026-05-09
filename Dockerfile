FROM python:3.10
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
COPY frontend/ ./frontend/
RUN python manage.py collectstatic --noinput
CMD gunicorn core.wsgi:application --bind 0.0.0.0:$PORT