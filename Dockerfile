FROM python:3.11-slim-buster
MAINTAINER Zech Zimmerman "hi@zech.codes"

WORKDIR /usr/src/app

RUN pip install --no-cache-dir poetry
RUN poetry config virtualenvs.in-project true

COPY pyproject.toml .
COPY poetry.lock .
RUN poetry install

WORKDIR /usr/src/app

RUN mkdir -p /usr/src/app/tmp
ENV TMPDIR /usr/src/app/tmp

COPY ./bobbins ./bobbins

CMD ["poetry", "run", "python", "-OO", "-u", "-m", "bobbins"]
