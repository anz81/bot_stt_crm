from enum import Enum

class ACTIONS(Enum):
    UNDEFINED = 0
    CREATE = 1
    CHANGE = 2
    DELETE = 3
    UNPARSED = 4

class SUBJECTS(Enum):
    UNDEFINED = 0
    CONTACT = 1
    TASK = 2
    UNPARSED = 3

class ATTRIBUTES(Enum):
    NAME = 1
    PHONE = 2
    DATE = 3
    IN_TIME = 4
    FROM_TIME = 5
    TO_TIME = 6
    TASK_TYPE = 7
    UNPARSED = 8