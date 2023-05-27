FROM python:3.10

WORKDIR /app

COPY . .

ENV PORT=3000

EXPOSE $PORT

RUN apt install ffmpeg
RUN pip install -r requirements.txt

CMD ["python", "telegram.py"]