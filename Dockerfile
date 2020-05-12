FROM python:3.7-slim-buster
COPY . /
WORKDIR /
RUN apt-get \
        g++ \
        python-dev \
        libxml2 \
        libxml2-dev
RUN apt-get libxslt-dev
RUN pip install -r requirements.txt
ENTRYPOINT [ "python3.7" ]
CMD [ "app.py" ]