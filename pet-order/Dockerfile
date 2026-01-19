FROM python:alpine3.17

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY appPetOrder.py .

EXPOSE 8080

CMD ["python", "appPetOrder.py"]