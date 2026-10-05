# One image, three roles (server, honest household, compromised household). Keeping
# them in one image is deliberate: it makes explicit that a compromised household
# runs the same software as an honest one, differing only in which entrypoint the
# attacker starts.
FROM python:3.11-slim

RUN pip install --no-cache-dir \
      torch==2.4.1 --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir "flwr==1.23.0" numpy

WORKDIR /app
COPY fl_common.py fl_client.py fl_client_malicious.py fl_server.py /app/
ENV PYTHONUNBUFFERED=1
