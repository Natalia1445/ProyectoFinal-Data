# Imagen base
FROM python:3.11-slim

# Paquetes del sistema (para instalar awscli v2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl unzip ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Instalar AWS CLI v2 dentro del contenedor
RUN curl -sSL "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "/tmp/awscliv2.zip" \
 && unzip /tmp/awscliv2.zip -d /tmp \
 && /tmp/aws/install \
 && rm -rf /tmp/aws /tmp/awscliv2.zip

# Dependencias Python (nota: usa python-dotenv, no "dotenv")
RUN pip install --no-cache-dir \
    streamlit \
    mysql-connector-python \
    pandas \
    matplotlib \
    seaborn \
    python-dotenv \
    boto3 \
    plotly.express

# Directorio de trabajo
WORKDIR /app

# Copiar tu app
COPY dashboard.py /app/

# Puerto
EXPOSE 8502

# Comando
CMD ["streamlit", "run", "dashboard.py", "--server.port=8502", "--server.address=0.0.0.0"]
