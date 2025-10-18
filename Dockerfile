FROM python:3.11-slim

COPY ./bot /usr/bot
COPY requirements.txt /usr/bot
COPY .env /usr/bot
WORKDIR /usr/bot

RUN pip install --upgrade pip \
  && pip install -r requirements.txt

CMD ["python", "src/bot.py"]
