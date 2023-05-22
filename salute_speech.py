import datetime
import requests
import uuid
from consts import SALUTE_SPEECH_AUTHORIZE_DATA

class Salute_Speech():

    def __init__(self):
        self.uuid = uuid.uuid4()
        self.token = ''
        self.token_expiration = 0
        self.get_token()

    def get_token(self):
        headers = {
            'authorization': f'Basic {SALUTE_SPEECH_AUTHORIZE_DATA}',
            'RqUID': f'{self.uuid}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        data = {
            'scope': 'SALUTE_SPEECH_PERS'
        }
        response = requests.post(
            url='https://ngw.devices.sberbank.ru:9443/api/v2/oauth',
            headers=headers,
            data=data,
            verify=False
        )
        if response.status_code == 200:
            result = response.json()
            self.token = result['access_token']
            self.token_expiration = result['expires_at']

    def update_headers(self, headers=None):
        if not headers:
            headers = {}
        date = datetime.datetime.now()
        if date.timestamp() >= self.token_expiration - 1000:
            self.get_token()
        headers['Authorization'] = f'Bearer {self.token}'
        return headers

    def recognize(self, filename):
        headers = {'Content-Type': 'audio/ogg;codecs=opus'}
        headers = self.update_headers(headers)
        with open(filename, 'rb') as f:
            response = requests.post(
                url='https://smartspeech.sber.ru/rest/v1/speech:recognize',
                headers=headers,
                files={'report.xls': f},
                verify=False
            )
            if response.status_code == 200:
                text = ''
                for sentence in response.json()['result']:
                    text += sentence
                return {'status': True, 'text': text}
        return {'status': False, 'text': 'Не получилось распознать текст'}

    def caps_words(self, text):
        words = text.split(' ')
        for i in range(0, len(words)):
            words[i] = words[i].capitalize()
        return ' '.join(words)