# Usa una imagen oficial de Python más ligera
FROM python:3.11-slim

# Establece el directorio de trabajo
WORKDIR /app

# Copia los archivos del proyecto al contenedor
COPY . /app

# Actualiza los paquetes del sistema para reducir vulnerabilidades
RUN apt-get update && apt-get upgrade -y && apt-get clean

# Instala las dependencias
RUN pip install --upgrade pip
RUN pip install django djangorestframework

# Expone el puerto 8000
EXPOSE 8000

# Comando para iniciar el servidor
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]