FROM python:3.10.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /home/web

COPY ./ /home/web/

RUN pip install -r /home/web/requirements.txt
