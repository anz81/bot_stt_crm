import datetime
import re
from natasha import Segmenter, MorphVocab, NewsEmbedding, NewsMorphTagger, NewsSyntaxParser, NewsNERTagger, \
    PER, LOC, NamesExtractor, DatesExtractor, Doc, DocSpan
from enums import ACTIONS, SUBJECTS
from bot_dict import bot_dict


def part_of_date_to_str(part):
    if part < 10:
        return f'0{part}'
    else:
        return str(part)

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

        self.segmenter = Segmenter()
        self.morph_vocab = MorphVocab()
        emb = NewsEmbedding()
        self.morph_tagger = NewsMorphTagger(emb)
        self.syntax_parser = NewsSyntaxParser(emb)
        self.ner_tagger = NewsNERTagger(emb)
        self.names_extractor = NamesExtractor(self.morph_vocab)
        dates_extractor = DatesExtractor(self.morph_vocab)

        self.doc = Doc(message)
        self.doc.segment(self.segmenter)
        self.doc.tag_morph(self.morph_tagger)
        self.doc.tag_ner(self.ner_tagger)
        self.doc.parse_syntax(self.syntax_parser)
        left_tokens = []
        # print(self.doc.tokens)
        for i in range(0, len(self.doc.tokens)):
            left_tokens.append(i)
        for i in range(0, len(self.doc.tokens)):
            if not i in left_tokens:
                continue
            self.doc.tokens[i].lemmatize(self.morph_vocab)
            result = self.get_dict_keys(self.doc.tokens, i)
            if result['found']:
                if result['up_key'] in ['action', 'subject']:       # если нашлось дейсвие или субъект
                    payload[result['up_key']] = bot_dict[result['up_key']][result['down_key']]['code']
                    left_tokens.remove(i)
                elif result['up_key'] == 'task_type':                 # если нашелся тип задачи
                    payload['attributes']['task_type'] = bot_dict[result['up_key']][result['down_key']]['code']
                    for j in range(0, result['parts_value']):
                        left_tokens.remove(i + j)
                elif result['up_key'] == 'date_phrase':               # если нашлась отсылка к дате
                    date = datetime.datetime.now()
                    date += datetime.timedelta(days=bot_dict[result['up_key']][result['down_key']]['code'])
                    payload['attributes']['date'] = date.date()
                    left_tokens.remove(i)
            elif self.doc.tokens[i].pos == 'ADP' and self.doc.tokens[i].rel == 'case':          # выделяем время задачи
                result = self.parse_time_event(i, payload, left_tokens)
                if result:
                    payload, left_tokens = result

        if not payload['attributes']['date']:
            matches = dates_extractor(message)                          # ищем даты в тексте
            dates = [i.fact.as_json for i in matches]
            if len(dates) > 0:
                payload['attributes']['date'] = self.form_date(dates[0])
                values = []
                value_str = ''
                if 'day' in dates[0].keys():
                    values.append(str(dates[0]['day']))
                    value_str = part_of_date_to_str(dates[0]['day'])
                if 'month' in dates[0].keys():
                    values.append(str(dates[0]['month']))
                    value_str += '.' + part_of_date_to_str(dates[0]['month'])
                if 'year' in dates[0].keys():
                    values.append(str(dates[0]['year']))
                    value_str += '.' + str(dates[0]['year'])
                for i in range(0, len(self.doc.tokens)):
                    if self.doc.tokens[i].text in values or value_str in self.doc.tokens[i].text:
                        left_tokens.remove(i)

        payload['attributes']['name'], left_tokens = self.get_name(message, left_tokens)        # ищем ФИО в тексте

        if not payload['attributes']['in_time']:                    # попробуем дожать время, если до этого не нашли
            for i in left_tokens:
                if len(self.doc.tokens[i].text) == 4 and 'Case' in self.doc.tokens[i].feats.keys() and 'Nom' == self.doc.tokens[i].feats['Case']:
                #     if not i == 0 or not i == len(self.doc.tokens - 1):
                #         if not ('Nom' == self.doc.tokens[i - 1].feats['Case'] or 'Nom' == self.doc.tokens[i + 1].feats['Case']):
                            try:
                                hours = int(self.doc.tokens[i].text[:2])
                                minutes = int(self.doc.tokens[i].text[2:])
                                payload['attributes']['in_time'] = datetime.time(hours, minutes, 0, 0)
                                left_tokens.remove(i)
                            except Exception as e:
                                pass
                elif ':' in self.doc.tokens[i]:
                    if i - 1 in left_tokens and i + 1 in left_tokens:
                        try:
                            hours = int(self.doc.tokens[i - 1].text)
                            minutes = int(self.doc.tokens[i + 1].text)
                            payload['attributes']['in_time'] = datetime.time(hours, minutes, 0, 0)
                            left_tokens.remove(i - 1)
                            left_tokens.remove(i + 1)
                            left_tokens.remove(i)
                        except Exception as e:
                            pass


        last_phone = ''
        for t in left_tokens:
            if not self.doc.tokens[t].pos == 'PUNCT':
                last_phone += self.doc.tokens[t].text

        phone_items = self.phone_extract(last_phone.replace(',', '').replace('.', ''))
        if len(phone_items) > 0:
            payload['attributes']['phone'] = phone_items[0]
        
        if payload['action'] == ACTIONS.UNPARSED and payload['subject'] == SUBJECTS.UNPARSED and \
            payload['attributes']['phone'] != None and \
            (payload['attributes']['first_name'] != None or payload['attributes']['last_name']):
                payload['action'] = ACTIONS.CREATE
                payload['subject'] = SUBJECTS.CONTACT
                
        print(payload)
        return payload

    def get_name(self, message, left_tokens):
        names = [i.fact for i in self.names_extractor(message)]
        if len(names) == 0:
            return '', left_tokens
        new_left_tokens = left_tokens.copy()
        fio_tokens = {
            'last': None,
            'first': None,
            'middle': None
        }
        for name in names:
            for i in left_tokens:
                token = self.doc.tokens[i]
                if name.last and token.text == name.last:
                    if token.pos == 'PROPN' or (token.pos == 'NOUN' and fio_tokens['last'] == None):
                        fio_tokens['last'] = token
                        new_left_tokens.remove(i)
                elif name.first and token.text == name.first:
                    if token.pos == 'PROPN' or (token.pos == 'NOUN' and fio_tokens['first'] == None):
                        fio_tokens['first'] = token
                        new_left_tokens.remove(i)
                elif name.middle and token.text == name.middle:
                    if token.pos == 'PROPN' or (token.pos == 'NOUN' and fio_tokens['middle'] == None):
                        fio_tokens['middle'] = token
                        new_left_tokens.remove(i)
        text = ''
        tokens = []
        gender = 'Fem'
        start_pos = 0
        if fio_tokens['first']:
            gender = fio_tokens['first'].feats['Gender']
        for key in fio_tokens.keys():
            if fio_tokens[key]:
                fio_tokens[key].start = start_pos
                start_pos += len(fio_tokens[key].text)
                fio_tokens[key].stop = start_pos - 1
                if len(text) > 0:
                    text += ' '
                text += fio_tokens[key].text
                fio_tokens[key].feats['Gender'] = gender
                fio_tokens[key].text = fio_tokens[key].text.capitalize()
                tokens.append(fio_tokens[key])
        doc_span = DocSpan(0, start_pos - 1, 'PER', text, tokens)
        doc_span.normalize(self.morph_vocab)
        return doc_span.normal, new_left_tokens

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
        new_left_tokens = left_tokens.copy()
        new_left_tokens.remove(i)

        token = self.doc.tokens[i + 1]
        # if token.id == head_id:
            # if token.text == 'часов':                             # TODO: время можно написать в формате восемь часов пять минут
            #     event_time = ''                                   # этот кейс сейчас не обрабатывается
        # if token.rel == 'nummod':
        if len(token.text) == 4:
            try:
                hours = int(token.text[:2])
                minutes = int(token.text[2:])
                event_time = datetime.time(hours, minutes, 0, 0)
                new_left_tokens.remove(i + 1)
            except Exception:
                print('>>>>>>>> Can\'t parse time!!! p.0')
                print(self.doc.tokens)
        elif '-' in token.text:                               # если время записано в формате 19-30
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
        elif self.doc.tokens[i + 2].text == ':':              # если время записано в формате 19:30
            try:
                hours = int(token.text)
                minutes = int(self.doc.tokens[i + 3].text)
                event_time = datetime.time(hours, minutes, 0, 0)
                for j in range(1, 4):
                    new_left_tokens.remove(i + j)

            except Exception:
                print('>>>>>>>> Can\'t parse time!!! p.3')
                print(self.doc.tokens)
        elif len(token.text) <= 2:
            try:
                hours = int(token.text)
                event_time = datetime.time(hours, 0, 0, 0)
                new_left_tokens.remove(i + 1)
            except Exception:
                print('>>>>>>>> Can\'t parse time!!! p.0')
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
                valid_items.append(item.replace('-', ''))
        return valid_items

    def get_dict_keys(self, tokens, index):
        for up_key in bot_dict.keys():
            for down_key in bot_dict[up_key].keys():
                values = bot_dict[up_key][down_key]['values']
                if tokens[index].lemma.lower() in values or tokens[index].text.lower() in values:
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
