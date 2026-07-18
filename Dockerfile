# Imagen base
FROM python:3.12-slim

# Desactiva archivos .pyc.
ENV PYTHONDONTWRITEBYTECODE=1
# Envía los registros sin búfer.
ENV PYTHONUNBUFFERED=1

# Directorio de trabajo
WORKDIR /app

# Copia las dependencias.
COPY requirements.txt .

# Instala dependencias.
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copia el proyecto.
COPY . .

# Expone el puerto 8000.
EXPOSE 8000

# Migra e inicia el servidor.
CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]
