import datetime
import re
from natasha import Segmenter, MorphVocab, NewsEmbedding, NewsMorphTagger, NewsSyntaxParser, NewsNERTagger, \
    PER, LOC, NamesExtractor, DatesExtractor, Doc
from enums import ACTIONS, SUBJECTS
from bot_dict import bot_dict


class Parse_client:
    def parse(self, message):
        payload = {
            'action': ACTIONS.UNDEFINED,
            'subject': SUBJECTS.UNDEFINED,
            'attributes': {
                'name': None,
                'phone': None,
                'date': None,
                'in_time': None,
                'from_time': None,
                'to_time': None,
                'task_type': None,
            }
        }

        segmenter = Segmenter()
        morph_vocab = MorphVocab()
        emb = NewsEmbedding()
        morph_tagger = NewsMorphTagger(emb)
        syntax_parser = NewsSyntaxParser(emb)
        ner_tagger = NewsNERTagger(emb)
        names_extractor = NamesExtractor(morph_vocab)
        dates_extractor = DatesExtractor(morph_vocab)

        self.doc = Doc(message)
        self.doc.segment(segmenter)
        self.doc.tag_morph(morph_tagger)
        self.doc.tag_ner(ner_tagger)
        self.doc.parse_syntax(syntax_parser)
        left_tokens = []
        for i in range(0, len(self.doc.tokens)):
            left_tokens.append(i)
        for i in range(0, len(self.doc.tokens)):
            token = self.doc.tokens[i]
            token.lemmatize(morph_vocab)
            if token.pos == 'VERB' and (token.rel == 'root' or token.rel == 'xcomp'):         # выделяем что какое действие нужно совершить
                payload['action'] = self.parse_action(token.lemma)
                left_tokens.remove(i)
            if token.pos == 'NOUN' and token.rel == 'obj':          # выделяем с каким субъектом нужно совершить действие
                payload['subject'] = self.parse_subject(token.lemma)
                left_tokens.remove(i)
            if token.pos =='VERB' and token.rel == 'nmod':          # выделяем тип задачи
                payload['attributes']['task_type'] = self.get_task_type(token.lemma)
                left_tokens.remove(i)
            if token.pos == 'ADP' and token.rel == 'case':          # выделяем время задачи
                payload, left_tokens = self.parse_time_event(i, payload, left_tokens)

        matches = dates_extractor(message)                          # ищем даты в тексте
        dates = [i.fact.as_json for i in matches]
        if len(dates) > 0:
            payload['attributes']['date'] = self.form_date(dates[0])
            values = []
            if 'year' in dates[0].keys():
                values.append(str(dates[0]['year']))
            if 'month' in dates[0].keys():
                values.append(str(dates[0]['month']))
            if 'day' in dates[0].keys():
                values.append(str(dates[0]['day']))
            for i in range(0, len(self.doc.tokens)):
                if self.doc.tokens[i].text in values:
                    left_tokens.remove(i)

        if len(self.doc.spans) > 0:                                 # ищем ФИО в тексте
            self.doc.spans[0].normalize(morph_vocab)
            payload['attributes']['name'] = self.doc.spans[0].normal
            fio = self.doc.spans[0].text.split(' ')
            for i in range(0, len(self.doc.tokens)):
                if self.doc.tokens[i].text in fio:
                    left_tokens.remove(i)

        last_phone = ''
        for t in left_tokens:
            last_phone += self.doc.tokens[t].text

        phone_items = self.phone_extract(last_phone)
        if len(phone_items) > 0:
            payload['attributes']['phone'] = phone_items[0]

        print(payload)
        return payload

    def parse_action(self, word):
        if word in bot_dict['commands']['create']:
            return ACTIONS.CREATE
        if word in bot_dict['commands']['change']:
            return ACTIONS.CHANGE
        if word in bot_dict['commands']['delete']:
            return ACTIONS.DELETE
        return ACTIONS.UNPARSED

    def parse_subject(self, word):
        match word:
            case 'задача': return SUBJECTS.TASK
            case 'контакт': return SUBJECTS.CONTACT
            case _: return SUBJECTS.UNPARSED

    def form_date(self, date_obj):
        day = 0
        month = 0
        year = 0
        today = datetime.datetime.now()
        if (date_obj.get('day')):           # парсим день
            day = date_obj.get('day')
        else:
            day = today.day             # если нет, берем текущий
        if (date_obj.get('month')):         # парсим месяц
            month = date_obj.get('month')
        else:
            month = today.month         # если нет, берем текущий
        if (date_obj.get('year')):          # парсим год
            year = date_obj.get('year')
        else:                           # если нет, берем текущий, либо следующий если дата указана меньше текущей
            if month > today.month or (month == today.month and day >= today.day):
                year = today.year
            else:
                year = today.year + 1
        return(datetime.date(year, month, day))

    def parse_time_event(self, i, payload, left_tokens):
        _payload = payload
        event_time = None
        if self.doc.tokens[i].text not in ('с', 'в', 'по'):         # если не эти 3 предлога, то выходим
            return None
        new_left_tokens = left_tokens
        new_left_tokens.remove(i)

        head_id = self.doc.tokens[i].head_id                        # ищем токены с указанным head_id
        token = self.doc.tokens[i + 1]
        if token.id == head_id:
            # if token.text == 'часов':                             # TODO: время можно написать в формате восемь часов пять минут
            #     event_time = ''                                   # этот кейс сейчас не обрабатывается
            if token.rel == 'nummod':
                if '-' in token.text:                               # если время записано в формате 19-30
                    time_part = token.text.split('-')
                    if len(time_part) != 2:
                        print('>>>>>>>> Can\'t parse time!!! p.1')
                        print(self.doc.tokens)
                    try:
                        hours = int(time_part[0])
                        minutes = int(time_part[1])
                        event_time = datetime.time(hours, minutes, 0, 0)
                        new_left_tokens.remove(i + 1)
                    except Exception:
                        print('>>>>>>>> Can\'t parse time!!! p.2')
                        print(self.doc.tokens)
                if self.doc.tokens[i + 2].text == ':':              # если время записано в формате 19:30
                    try:
                        hours = int(token.text)
                        minutes = int(self.doc.tokens[i + 3].text)
                        event_time = datetime.time(hours, minutes, 0, 0)
                        for j in range(1, 4):
                            new_left_tokens.remove(i + j)

                    except Exception:
                        print('>>>>>>>> Can\'t parse time!!! p.3')
                        print(self.doc.tokens)
        if event_time:
            match self.doc.tokens[i].text:
                case 'с':
                    _payload['attributes']['in_time'] = event_time   # было from_time но оно вроде как не надо
                case 'в':
                    _payload['attributes']['in_time'] = event_time
                case 'по':
                    _payload['attributes']['to_time'] = event_time
        return _payload, new_left_tokens

    def phone_extract(self, text):
        items = [
            m.group()
            for m in re.finditer(r"((8|\+7)[\- ]?)?(\(?\d{3}\)?[\- ]?)?[\d\- ]{7,10}", text)
        ]
        valid_items = []
        for item in items:
            if len(item.replace(' ', '')) > 5:
                valid_items.append(item)
        return valid_items

    def get_task_type(text):
        for t in bot_dict['task_types'].keys():
            if text in bot_dict['task_types'][t]:
                return t
        return 'не определено'
