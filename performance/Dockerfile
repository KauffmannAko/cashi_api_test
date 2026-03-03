FROM python:3.11-slim

WORKDIR /workspace/performance

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY . /workspace/performance

EXPOSE 8089

CMD ["locust", "-f", "locustfile.py"]
