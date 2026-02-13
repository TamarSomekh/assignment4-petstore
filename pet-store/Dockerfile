# FROM python:alpine3.17

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY appPetStore.py .

ARG STORE_ID
ENV STORE_ID=${STORE_ID}
ENV NINJA_API_KEY=V00gLHAVVVI2hzOBGlyZKw==AYJdHaNxAMDY7zEI

EXPOSE 8000

CMD ["python", "appPetStore.py"]
