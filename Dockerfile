# Use the official lightweight Python image.
# https://hub.docker.com/_/python
FROM python:3.6.12-slim

# Copy local code to the container image.
ENV APP_HOME /app
WORKDIR $APP_HOME
COPY . ./

RUN apt update && apt install -y \
    libgl1-mesa-glx \
    libglib2.0-dev

# Install production dependencies.
RUN pip install --upgrade pip

RUN pip install -r requirements.txt

EXPOSE 8080

# Run the web service on container startup. Here we use the gunicorn
# webserver, with one worker process and 8 threads.
# For environments with multiple CPU cores, increase the number of workers
# to be equal to the cores available.

RUN chmod -R 777 run.sh

CMD ./run.sh

# CMD exec gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 0 app:app