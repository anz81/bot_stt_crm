import telebot
import uuid
import os
import speech_recognition as sr
from crm_client import CRM_client
from parse_client import Parse_client
from consts import TELEGRAM_API_KEY

bot = telebot.TeleBot(TELEGRAM_API_KEY)
r = sr.Recognizer()

def recognise(filename):
    with sr.AudioFile(filename) as source:
        audio_text = r.listen(source)
        try:
            print('Converting audio transcripts into text ...')
            text = r.recognize_google(audio_text,language='ru_RU')
            print(text)
            return {'status': True, 'text': text}
        except:
            print('Sorry.. run again...')
            return {'status': False, 'text': 'Не могу распознать текст, попробуйте еще...'}

def reply_to_bot(message, result):
    text = ''
    if not result['status']:
        text = 'ОШИБКА!\n'
    else:
        text = 'УСПЕШНО!\n'
    text += result['text']
    bot.reply_to(message, text)

def process_command(message):
    get_actions = parse_client.parse(message.text)
    result = crm_client.proceed_actions(get_actions, message)
    reply_to_bot(message, result)

@bot.message_handler(commands=['help', 'start'])
def send_welcome(message):
    bot.reply_to(message, """\
Привет, я могу отправлять сообщения в CRM.
Введите текст, или надиктуйте сообщение что я должен сделать\
""")

@bot.message_handler(content_types=['text'])
def get_text_messages(message):
    process_command(message)

@bot.message_handler(content_types=['voice'])
def voice_processing(message):
    filename = str(uuid.uuid4())
    file_name_full="./voice/"+filename+".ogg"
    file_name_full_converted="./ready/"+filename+".wav"
    file_info = bot.get_file(message.voice.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    with open(file_name_full, 'wb') as new_file:
        new_file.write(downloaded_file)
    os.system("ffmpeg -i " + file_name_full + "  " + file_name_full_converted)
    try:
        result = recognise(file_name_full_converted)
        if not result['status']:
            return reply_to_bot(message, result)
        message.text = result['text']
        # bot.reply_to(message, result['text'])
        process_command(message)
    except Exception as e:
        print(e)
    os.remove(file_name_full)
    # os.remove(file_name_full_converted)

crm_client = CRM_client()
parse_client = Parse_client()

bot.infinity_polling()
