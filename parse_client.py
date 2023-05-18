import datetime
import re
from natasha import Segmenter, MorphVocab, NewsEmbedding, NewsMorphTagger, NewsSyntaxParser, NewsNERTagger, \
    PER, LOC, NamesExtractor, DatesExtractor, Doc
from enums import ACTIONS, SUBJECTS
from bot_dict import bot_dict


class Parse_client:
    def parse(self, message):
        payload = {
            'action': ACTIONS.UNPARSED,
            'subject': SUBJECTS.UNPARSED,
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
            self.doc.tokens[i].lemmatize(morph_vocab)
            result = self.get_dict_keys(self.doc.tokens, i)
            if result['found']:
                if result['up_key'] in ['action', 'subject']:       # если нашлось дейсвие или субъект
                    payload[result['up_key']] = bot_dict[result['up_key']][result['down_key']]['code']
                    left_tokens.remove(i)
                if result['up_key'] == 'task_type':                 # если нашелся тип задачи
                    payload['attributes']['task_type'] = bot_dict[result['up_key']][result['down_key']]['code']
                    for j in range(0, result['parts_value']):
                        left_tokens.remove(i + j)
                if result['up_key'] == 'date_phrase':               # если нашлась отсылка к дате
                    date = datetime.datetime.now()
                    date += datetime.timedelta(days=bot_dict[result['up_key']][result['down_key']]['code'])
                    payload['attributes']['date'] = date.date()
                    left_tokens.remove(i)
            if self.doc.tokens[i].pos == 'ADP' and self.doc.tokens[i].rel == 'case':          # выделяем время задачи
                result = self.parse_time_event(i, payload, left_tokens)
                if result:
                    payload, left_tokens = result

        if not payload['attributes']['date']:
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

        if not payload['attributes']['in_time']:                    # попробуем дожать время, если до этого не нашли
            for i in left_tokens:
                print(self.doc.tokens[i].feats)
                if len(self.doc.tokens[i].text) == 4 and 'Nom' == self.doc.tokens[i].feats['Case']:
                #     if not i == 0 or not i == len(self.doc.tokens - 1):
                #         if not ('Nom' == self.doc.tokens[i - 1].feats['Case'] or 'Nom' == self.doc.tokens[i + 1].feats['Case']):
                            try:
                                hours = int(self.doc.tokens[i].text[:2])
                                minutes = int(self.doc.tokens[i].text[2:])
                                payload['attributes']['in_time'] = datetime.time(hours, minutes, 0, 0)
                                left_tokens.remove(i)
                            except Exception as e:
                                pass

        last_phone = ''
        for t in left_tokens:
            last_phone += self.doc.tokens[t].text

        phone_items = self.phone_extract(last_phone)
        if len(phone_items) > 0:
            payload['attributes']['phone'] = phone_items[0]

        print(payload)
        return payload

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
        if self.doc.tokens[i].text not in ('с', 'в', 'по', 'до'):         # если не эти 3 предлога, то выходим
            return None
        new_left_tokens = left_tokens
        new_left_tokens.remove(i)

        head_id = self.doc.tokens[i].head_id                        # ищем токены с указанным head_id
        token = self.doc.tokens[i + 1]
        if token.id == head_id:
            # if token.text == 'часов':                             # TODO: время можно написать в формате восемь часов пять минут
            #     event_time = ''                                   # этот кейс сейчас не обрабатывается
            if token.rel == 'nummod':
                if len(token.text) == 4:
                    try:
                        hours = int(token.text[:2])
                        minutes = int(token.text[2:])
                        event_time = datetime.time(hours, minutes, 0, 0)
                        new_left_tokens.remove(i + 1)
                    except Exception:
                        print('>>>>>>>> Can\'t parse time!!! p.0')
                        print(self.doc.tokens)
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
                case 'до':
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

    def get_dict_keys(self, tokens, index):
        for up_key in bot_dict.keys():
            for down_key in bot_dict[up_key].keys():
                values = bot_dict[up_key][down_key]['values']
                if tokens[index].lemma in values:
                    return {'found': True, 'up_key': up_key, 'down_key': down_key, 'parts_value': 1}
                for value in values:
                    if ' ' in value:
                        word_parts = value.split(' ')
                        if index <= len(tokens) - len(word_parts):
                            flag = True
                            for i in range(0, len(word_parts)):
                                if not tokens[index + i].text == word_parts[i]:
                                    flag = False
                                    break
                            if flag:
                                return {'found': True, 'up_key': up_key, 'down_key': down_key, 'parts_value': len(word_parts)}
        return {'found': False}
