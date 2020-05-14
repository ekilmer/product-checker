FROM python:3.7.4-slim

ADD requirements.txt /app
WORKDIR /app
RUN pip install -r requirements.txt

ADD . /app

ENTRYPOINT [ "python3.7" ]
CMD [ "app.py" ]