from enums import ACTIONS, SUBJECTS, TASK_TYPE
bot_dict = {
    'action': {
        'create': {'values': ['создай', 'создать', 'сделать', 'сделай'], 'code': ACTIONS.CREATE},
        'change': {'values': ['измени', 'изменить', 'исправь', 'исправить'], 'code': ACTIONS.CHANGE},
        'delete': {'values': ['удали', 'удалить', ], 'code': ACTIONS.DELETE},
    },
    'subject': {
        'task': {'values': ['задача'], 'code': SUBJECTS.TASK},
        'contact': {'values': ['контакт'], 'code': SUBJECTS.CONTACT}
    },
    'task_type': {
        'call': {'values': ['позвонить', 'связаться'], 'code': TASK_TYPE.CALL},
        'take_in': {'values': ['привоз', 'при воз', 'при ваз', 'при вас'], 'code': TASK_TYPE.TAKE_IN},
        'take_off': {'values': ['отвоз', 'от воз', 'от вас', 'от ваз'], 'code': TASK_TYPE.TAKE_OFF},
    },
    'date_phrase': {
        'tomorrow': {'values': ['завтра'], 'code': 1},
        'after_tomorrow': {'values': ['послезавтра'], 'code': 2}
    }
}