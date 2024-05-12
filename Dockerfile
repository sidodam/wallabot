FROM --platform=linux/arm64/v8 python:3.8-slim-buster
WORKDIR /wallabot-app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY ./app ./app

CMD [ "python", "./app/wallabot.py"]