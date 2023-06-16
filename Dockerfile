FROM python:3.10

WORKDIR /app

COPY . .

ENV PORT=3000

EXPOSE $PORT

RUN apt-get -y update
RUN apt-get -y upgrade
RUN apt-get install -y ffmpeg
RUN pip install -r requirements.txt

CMD ["python", "telegram.py"]