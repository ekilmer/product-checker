FROM python:3.7-slim
COPY . /
WORKDIR /
RUN pip install -r requirements.txt
ENTRYPOINT [ "python3.7" ]
CMD [ "app.py" ]