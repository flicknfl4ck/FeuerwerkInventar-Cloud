# Basis-Image von Python 3.10
FROM python:3.10-slim

# Setze das Arbeitsverzeichnis im Container
WORKDIR /app

# Kopiere die Abhängigkeiten und installiere sie
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopiere den Rest deines Codes (app.py) in den Container
COPY . .

# Definiere den Port, den Streamlit verwenden soll
EXPOSE 8501

# Der Befehl, der die Streamlit-App startet und sie auf allen IP-Adressen (0.0.0.0) freigibt
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]