import datetime
from amocrm_api.v2 import tokens, Task, Contact as _Contact, Lead as _Lead, custom_field
from consts import CRM_CLIENT_ID, CRM_CLIENT_SECRET, CRM_SUBDOMAIN, CRM_REDIRECT, CRM_CODE
from enums import ACTIONS, SUBJECTS, TASK_TYPE

test_payload = {
    'action': ACTIONS.CREATE,
    'subject': SUBJECTS.TASK,
    'attributes': {
        'name': 'Иван Иванович Иванов',
        'phone': '(999)1112233',
        'date': datetime.date(2023, 5, 24),
        'in_time': None,
        'from_time': datetime.time(19, 0),
        'to_time': datetime.time(19, 30),
        'task_type': 'позвонить'
    }
}

def time_to_seconds(t):
    return (t.hour * 60 + t.minute) * 60

def get_task_type(task_type):
    match task_type:
        case TASK_TYPE.CALL:
            return 1
        case TASK_TYPE.TAKE_IN:
            return 2918958
        case TASK_TYPE.TAKE_OFF:
            return 2918962
        case _:
            return 1

# class Task(_Task):
    # telegram_name = custom_field.TextCustomField(name='Имя пользователя Телеграм', code='CF_T_TeleName', auto_create=True)
    # telegram_id = custom_field.TextCustomField(name='Id пользователя Телеграм', code='CF_T_TeleId', auto_create=True)
    # deleted = custom_field.TextCustomField(name='Задача удалена', code='CF_T_Deleted', auto_create=True)
    # type_task = custom_field.TextCustomField(name='Тип задачи', code='CF_T_TaskType', auto_create=True)

class Contact(_Contact):
    telegram_name = custom_field.TextCustomField(name='Имя пользователя Телеграм', field_id=38105)
    telegram_id = custom_field.TextCustomField(name='Id пользователя Телеграм', field_id=38157)
    phone = custom_field.TextCustomField(name='Телефон контакта', field_id=38159)

class Lead(_Lead):
    pass
    # telegram_name = custom_field.TextCustomField(name='Имя пользователя Телеграм',  code='CF_L_TeleName', auto_create=True)
    # telegram_id = custom_field.TextCustomField(name='Id пользователя Телеграм', code='CF_L_TeleId', auto_create=True)


class CRM_client:
    def __init__(self):
        tokens.default_token_manager(
            client_id=CRM_CLIENT_ID,
            client_secret=CRM_CLIENT_SECRET,
            subdomain=CRM_SUBDOMAIN,
            redirect_url=CRM_REDIRECT,
            storage=tokens.FileTokensStorage(),  # by default FileTokensStorage
        )
        tokens.default_token_manager.init(code=CRM_CODE, skip_error=True)

    def proceed_actions(self, payload, message):
        match payload['subject']:
            case SUBJECTS.CONTACT:
                match payload['action']:
                    case ACTIONS.CREATE:
                        return self.contact_create(payload, message)
                    case ACTIONS.CHANGE:
                        return self.contact_change(payload, message)
                    case ACTIONS.DELETE:
                        return self.contact_delete(payload, message)
                    case _:
                        return {'status': False, 'text': 'Ошибка в действии, я выполняю только следующие действия: создать, изменить, удалить'}
            case SUBJECTS.TASK:
                match payload['action']:
                    case ACTIONS.CREATE:
                        return self.task_create(payload, message)
                    case ACTIONS.CHANGE:
                        return self.task_change(payload, message)
                    case ACTIONS.DELETE:
                        return self.task_delete(payload, message)
                    case _:
                        return {'status': False, 'text': 'Ошибка в действии, я выполняю только следующие действия: создать, изменить, удалить'}
            case _:
                return {'status': False, 'text': 'Ошибка в субъекте, я работаю только со следующими сущностями: контакт, задача'}

    def contact_create(self, payload, message):
        contact_name = None
        contact_phone = None
        telegram_name = None
        telegram_id = None
        if 'name' in payload['attributes'].keys():
            contact_name = payload['attributes']['name']
        else:
            return {'status': False, 'text': 'Для создания контакта необходимо указать его ФИО'}
        contacts = list(filter(lambda c: c.name == contact_name, Contact.objects.all()))
        if len(contacts) > 0:
            return {'status': False, 'text': f'Контакт {contact_name} уже существует!'}
        if 'phone' in payload['attributes'].keys():
            contact_phone = payload['attributes']['phone']
        else:
            return {'status': False, 'text': 'Для создания контакта необходимо указать его телефон'}
        if message.from_user.first_name:
            telegram_name = message.from_user.first_name
        if message.from_user.username:
            telegram_id = message.from_user.username
        contact = Contact()
        contact.name=contact_name
        contact.phone=contact_phone
        contact.telegram_name=telegram_name
        contact.telegram_id=telegram_id
        contact.tags=[{'name':telegram_id}]
        # contact.text = message.text
        contact.save()
        return {'status': True, 'text': f'Контакт {contact_name} создан'}

    def contact_change(self, payload, message):
        contact_name = None
        contact_phone = None
        telegram_name = None
        telegram_id = None
        if 'name' in payload['attributes'].keys():
            contact_name = payload['attributes']['name']
        else:
            return {'status': False, 'text': 'Для изменения контакта необходимо указать его ФИО'}
        if 'phone' in payload['attributes'].keys():
            contact_phone = payload['attributes']['phone']
        else:
            return {'status': False, 'text': 'Для изменения контакта необходимо указать новый номер телефона'}
        if message.from_user.first_name:
            telegram_name = message.from_user.first_name
        if message.from_user.username:
            telegram_id = message.from_user.username
        contacts = list(filter(lambda c: contact_name in c.name, Contact.objects.all()))
        if len(contacts) > 0:
            contact = contacts[0]
            if not telegram_id == contact.telegram_id:
                return {'status': False, 'text': f'Вы не можете менять контакт {contact_name}'}
            contact.phone = contact_phone
            # if contact.text:
            #     contact.text += '\n' + message.text
            # else:
            #     contact.text = message.text
            contact.save()
            return {'status': True, 'text': f'Изменения для контакта {contact_name} внесены'}
        else:
            return {'status': False, 'text': f'Контакт {contact_name} не найден'}

    def contact_delete(self, payload, message):
        contact_name = None
        telegram_name = None
        telegram_id = None
        if 'name' in payload['attributes'].keys():
            contact_name = payload['attributes']['name']
        else:
            return 'Для удаления контакта необходимо указать его ФИО'
        if message.from_user.first_name:
            telegram_name = message.from_user.first_name
        if message.from_user.username:
            telegram_id = message.from_user.username
        contacts = list(filter(lambda c: contact_name in c.name, Contact.objects.all()))
        if len(contacts):
            contact = contacts[0]
            if telegram_id == contact.telegram_id:
                contact.tags = []
                # contact.text += '\n' + message.text
                contact.save()
                return {'status': True, 'text': f'Контакт {contact_name} удален'}
            else:
                return {'status': False, 'text': f'Вы не можете удалить контакт {contact_name}'}
        else:
            return {'status': False, 'text': f'Контакт {contact_name} не найден'}

    def task_create(self, payload, message):
        contact_name = None
        telegram_name = None
        telegram_id = None
        result_create = {'status': False, 'text': ''}
        if payload['attributes']['name']:
            contact_name = payload['attributes']['name']
        else:
            return {'status': False, 'text': 'Для создания задачи необходимо указать ФИО'}
        if message.from_user.first_name:
            telegram_name = message.from_user.first_name
        if message.from_user.username:
            telegram_id = message.from_user.username
        contacts = list(filter(lambda c: contact_name in c.name, Contact.objects.all()))
        contact = 0
        if len(contacts) == 0:
            result_create = self.contact_create(payload, message)
            if not result_create['status']:
                return result_create
            contact = list(filter(lambda c: c.name == contact_name, Contact.objects.all()))[0]
        else:
            contact = contacts[0]
        if telegram_id == contact.telegram_id:
            task = Task()
            if 'task_type' in payload['attributes'].keys():
                task.type_task = payload['attributes']['task_type']
            new_date = datetime.date.today()
            if not payload['attributes']['date'] == None:
                new_date = payload['attributes']['date']
            if not payload['attributes']['in_time'] == None:
                new_date = datetime.datetime.combine(new_date, payload['attributes']['in_time'])
                if not payload['attributes']['to_time'] == None:
                    task.duration_sec = time_to_seconds(payload['attributes']['to_time']) - time_to_seconds(payload['attributes']['in_time'])
            else:
                new_date = datetime.datetime.combine(new_date, datetime.time(23, 59, 59, 0))

            task.complete_till = new_date
            task.entity_id = contact.id
            task.entity_type = 'contacts'
            task.is_completed = False
            if not payload['attributes']['task_type'] == None:
                task.task_type_id = get_task_type(payload['attributes']['task_type'])
            task.text = message.text
            task.save()
            lead = Lead()
            lead.create()
            lead.contacts.append(contact)
            lead.save()
            return {'status': True, 'text': f'Задача для контакта {contact_name} создана\n{result_create["text"]}'}
        else:
            return {'status': False, 'text': f'Вы не можете создать задачу для {contact_name}'}

    def task_change(self, payload, message):
        contact_name = None
        telegram_name = None
        telegram_id = None
        if 'name' in payload['attributes'].keys():
            contact_name = payload['attributes']['name']
        else:
            return {'status': False, 'text': 'Для изменения задачи необходимо указать ФИО'}
        if message.from_user.first_name:
            telegram_name = message.from_user.first_name
        if message.from_user.username:
            telegram_id = message.from_user.username
        contacts = list(filter(lambda c: contact_name in c.name, Contact.objects.all()))
        if len(contacts) > 0:
            contact = contacts[0]
            if telegram_id == contact.telegram_id:
                tasks = Task.objects.all()
                task = Task()
                for t in tasks:
                    if t.entity_id == contact.id and t.task_type_id == get_task_type(payload['attributes']['task_type']) and not t.is_completed:
                        task = t
                        break
                if not task.id == None:
                    # if not payload['attributes']['task_type'] == None:
                    #     task.task_type_id = get_task_type(payload['attributes']['task_type'])
                    new_date = 0
                    if not payload['attributes']['date'] == None:
                        if not payload['attributes']['in_time'] == None:
                            new_date = datetime.datetime.combine(payload['attributes']['date'], payload['attributes']['in_time'])
                        else:
                            new_date = datetime.datetime.combine(payload['attributes']['date'], task.complete_till.time())
                    else:
                        if not payload['attributes']['in_time'] == None:
                            new_date = datetime.datetime.combine(task.complete_till.date(), payload['attributes']['in_time'])
                    if not new_date == 0:
                        task.complete_till = new_date
                    if not payload['attributes']['to_time'] == None:
                        task.duration_sec = time_to_seconds(payload['attributes']['to_time']) - time_to_seconds(task.complete_till.time())
                    task.text += '\n' + message.text
                    task.save()
                    return {'status': True, 'text': f'Задача для контакта {contact_name} изменена'}
                else:
                    return {'status': False, 'text': f'Нет открытых задач для контакта {contact_name}'}
            else:
                return {'status': False, 'text': f'Вы не можете изменить задачу для {contact_name}'}
        else:
            return {'status': False, 'text': f'Контакт {contact_name} не найден, задача не может быть изменена'}

    def task_delete(self, payload, message):
        contact_name = None
        telegram_name = None
        telegram_id = None
        if 'name' in payload['attributes'].keys():
            contact_name = payload['attributes']['name']
        else:
            return {'status': False, 'text': 'Для удаления задачи необходимо указать ФИО'}
        if message.from_user.first_name:
            telegram_name = message.from_user.first_name
        if message.from_user.username:
            telegram_id = message.from_user.username
        contacts = list(filter(lambda c: contact_name in c.name, Contact.objects.all()))
        if len(contacts) > 0:
            contact = contacts[0]
            if telegram_id == contact.telegram_id:
                task_filtered = list(filter(lambda t: t.entity_id == contact.id and t.task_type_id == get_task_type(payload['attributes']['task_type']) and not t.is_completed, Task.objects.all()))
                if len(task_filtered) > 0:
                    task = task_filtered[0]
                    task.is_completed = True
                    task.result = {'text': 'Задача удалена пользователем'}
                    task.text += '\n' + message.text
                    task.save()
                    leads = list(contact.leads)
                    if len(leads) > 0:
                        leads[0].status = 143
                        leads[0].closed_at = datetime.datetime.now()
                        leads[0].save()
                    return {'status': True, 'text': f'Задача для контакта {contact_name} удалена'}
                else:
                    return {'status': False, 'text': f'Нет незакрытых задач для контакта {contact_name}'}
            else:
                return {'status': False, 'text': f'Вы не можете удалить задачу для {contact_name}'}
        else:
            return {'status': False, 'text': f'Контакт {contact_name} не найден, задача не может быть удалена'}

    def temp(self):
        # tasks = Contact.objects.get(90389)  #
        # leads = list(tasks.leads)
        # data = {
        #     'lead[STATUS]': 143,
        #     'ID': 30413#leads[0].id
        # }
        # headers = {
        #     'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        #     'Accept': 'application/json, text/javascript, */*; q=0.01'
        # }
        # Lead.objects.request(method='POST', path='ajax/leads/detail/', headers=headers, data=data)
        # tasks = Contact.objects.get(90389)  #
        # leads = list(tasks.leads)
        # print(leads[0])

        lead = Lead.objects.get(30413)
        lead.status = 143
        lead.closed_at = datetime.datetime.now()
        lead.save()