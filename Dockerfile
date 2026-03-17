FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p app/static/uploads

EXPOSE 5000

CMD gunicorn -b 0.0.0.0:${PORT:-5000} -w 2 wsgi:app
