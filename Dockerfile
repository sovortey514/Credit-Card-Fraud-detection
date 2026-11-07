FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir "pyarrow>=15,<20"
COPY . .
CMD ["python", "app.py"]