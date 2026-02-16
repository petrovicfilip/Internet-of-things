FROM python:3.11-slim

WORKDIR /app

# (Opcionalno ali korisno) spreči buffering logova
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Instaliraj zavisnosti
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopiraj aplikaciju
COPY app ./app

# Generiši gRPC Python fajlove u image-u
RUN python -m grpc_tools.protoc \
  -I app/proto \
  --python_out=app/generated \
  --grpc_python_out=app/generated \
  app/proto/iot_readings.proto \
  && python -c "from pathlib import Path; Path('app/generated/__init__.py').touch()"

EXPOSE 50051

CMD ["python", "-m", "app.main"]