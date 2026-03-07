FROM python:3.11-slim
<<<<<<< HEAD
# Need these for OpenCV
RUN apt-get update && apt-get install -y \
libgl1-mesa-glx \
libglib2.0-0 \
&& rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
=======

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY producer.py /app/producer.py

>>>>>>> a07a24a3d90872702688a065bdae1136932c1afd
CMD ["python", "producer.py"]
