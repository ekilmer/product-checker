FROM python:3.7-slim-buster
COPY . /
WORKDIR /
RUN apt-get update
RUN apt-get install -y build-essential python3-lxml lxml --no-install-recommends
RUN apt-get purge -y --auto-remove build-essential
RUN apt-get clean
RUN pip install -r requirements.txt
ENTRYPOINT [ "python3.7" ]
CMD [ "app.py" ]