## BUILD STAGE
FROM dhi.io/python:3.11-alpine3.23-dev AS build-stage

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/usr/bot/venv/bin:$PATH"

WORKDIR /usr/bot

RUN python -m venv /usr/bot/venv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

## RUN STAGE
FROM dhi.io/python:3.11-alpine3.23-dev AS runtime-stage

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/usr/bot/venv/bin:$PATH"

WORKDIR /usr/bot

COPY ./bot /usr/bot
COPY --from=build-stage /usr/bot/venv /usr/bot/venv

CMD ["python", "src/bot.py"]
