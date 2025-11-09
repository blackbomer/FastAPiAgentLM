FROM python:3.11-slim

# Establece el directorio de trabajo
WORKDIR /app

# Instala dependencias del sistema mínimas
RUN apt-get update && \
    apt-get install -y \
        curl \
        && apt-get clean \
        && rm -rf /var/lib/apt/lists/*

# Copia requirements primero para cache de Docker
COPY requirements.txt .

# Instala dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto del proyecto
COPY . .

# Expone el puerto para FastAPI
EXPOSE 5000

# Comando de inicio del servidor
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5000"]
