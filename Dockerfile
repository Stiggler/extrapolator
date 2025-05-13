# Nutze ein leichtes Python-Image
FROM python:3.9-slim

# Verhindere das Schreiben von .pyc-Dateien und aktiviere unbuffered Output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Setze das Arbeitsverzeichnis auf /app
WORKDIR /app

# Kopiere die requirements.txt in das Arbeitsverzeichnis und installiere die Abhängigkeiten
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Kopiere den gesamten Projektcode in das Image
COPY . /app/

# Exponiere den Port, den deine Dash-App (standardmäßig 8050) nutzt
EXPOSE 8050

# Starte die App über gunicorn. "main:app" verweist auf die Datei main.py und das App-Objekt "app"
CMD ["gunicorn", "--workers", "1", "--bind", "0.0.0.0:8050", "main:app"]
