FROM python:3

# create app directory
WORKDIR /user/src/houndwave

COPY requirements.txt ./

RUN pip install -r requirements.txt

# bundle app source
COPY . .

EXPOSE 8000

CMD ["gunicorn", "index:app"]

