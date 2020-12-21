FROM python:3.8.1-alpine3.11

LABEL maintainer=""

ENV PYTHONUNBUFFERED 1

RUN mkdir /app
WORKDIR /app

COPY urlslogs ./urlslogs

COPY requirements-dev.txt .
COPY requirements.txt .
COPY manage.py .
COPY start.sh .


RUN apk update && apk add postgresql-dev gcc musl-dev
RUN pip3 install -r requirements.txt

ENTRYPOINT ./start.sh
