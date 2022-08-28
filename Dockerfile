FROM python:3

# create app directory
WORKDIR /user/src/houndwave

COPY requirements.txt ./

ENV YT_API_KEY=$YT_API_KEY
ENV CLIENT_SECRET=$CLIENT_SECRET
ENV CLIENT_ID=$CLIENT_ID
ENV HTTP_SERVER_URL=$HTTP_SERVER_URL
ENV SAVE_DIR=$SAVE_DIR

RUN pip install -r requirements.txt

# bundle app source
COPY . .

EXPOSE 8000

RUN apt-get -y update && apt-get -y upgrade && apt-get install -y --no-install-recommends ffmpeg

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "index:app" ]

