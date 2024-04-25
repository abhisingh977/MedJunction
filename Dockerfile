FROM python:3.8.0-slim

COPY src /src/
COPY requirements.txt /src/requirements.txt
COPY src/client_secret.json /src/client_secret.json
COPY src/medjunction.json /src/medjunction.json

WORKDIR /src

RUN pip install --upgrade pip

RUN pip3 install -r requirements.txt

ENV PORT 8080
ENV OAUTHLIB_INSECURE_TRANSPORT 1

EXPOSE 8080
# Run the web service on container startup
CMD exec gunicorn --bind :$PORT --workers 2 --threads 4 --timeout 600 main:app