FROM python:3.7-slim-buster
COPY . /
WORKDIR /

RUN apt-get update \
  && apt-get install -y build-essential python3-lxml --no-install-recommends \
  && pip install xmltodict lxml \
  && rm -rf /var/lib/apt/lists/* \
  && rm -rf /usr/share/doc && rm -rf /usr/share/man \
  && apt-get purge -y --auto-remove build-essential \
  && apt-get clean
RUN pip install -r requirements.txt
ENTRYPOINT [ "python3.7" ]
CMD [ "app.py" ]