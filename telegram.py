import telebot
import uuid
import os
import speech_recognition as sr
from crm_client import CRM_client
from parse_client import Parse_client
from consts import TELEGRAM_API_KEY
from salute_speech import Salute_Speech
from enums import ACTIONS, SUBJECTS

bot = telebot.TeleBot(TELEGRAM_API_KEY)
r = sr.Recognizer()
crm_client = CRM_client()
parse_client = Parse_client()

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
    proceed_actions(get_actions, message)

def proceed_actions(payload, message):
    result = crm_client.proceed_actions(payload, message)
    print(result['text'])
    reply_to_bot(message, result)

@bot.message_handler(commands=['help', 'start'])
def send_welcome(message):
    bot.reply_to(message, """\
Привет, я могу отправлять сообщения в CRM.
Введите текст, или надиктуйте сообщение что я должен сделать\
""")

@bot.message_handler(content_types=['contact'])
def get_contact_messages(message):
    payload = {
        'action': ACTIONS.CREATE,
        'subject': SUBJECTS.CONTACT,
        'attributes': {}
    }
    if message.contact.phone_number:
        payload['attributes']['phone'] = message.contact.phone_number
    fio = ''
    if hasattr(message.contact, 'first_name'):
        fio += message.contact.first_name
    if hasattr(message.contact, 'last_name'):
        if len(fio) > 0:
            fio += ' '
        fio += message.contact.last_name
    if hasattr(message.contact, 'middle_name'):
        if len(fio) > 0:
            fio += ' '
        fio += message.contact.middle_name
    payload['attributes']['name'] = fio
    print(payload)
    proceed_actions(payload, message)

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
    try:
        ss = Salute_Speech()
        result = ss.recognize(file_name_full)
        if not result['status']:
            os.system("ffmpeg -i " + file_name_full + "  " + file_name_full_converted)
            result = recognise(file_name_full_converted)
            os.remove(file_name_full_converted)
            if not result['status']:
                return reply_to_bot(message, result)
        print(result['text'])
        message.text = result['text']
        bot.reply_to(message, result['text'])
        process_command(message)
    except Exception as e:
        print(e)
    os.remove(file_name_full)

print('Bot started...')
bot.infinity_polling()
