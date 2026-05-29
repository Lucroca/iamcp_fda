FROM python:3.13-slim
WORKDIR /app
COPY requirements_remote.txt .
RUN pip install --no-cache-dir -r requirements_remote.txt
COPY . .
EXPOSE 8080
CMD ["python", "server_remote.py"]
