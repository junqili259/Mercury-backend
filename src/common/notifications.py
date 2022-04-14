from threading import Timer
from dateutil import parser
from datetime import datetime
from uuid import uuid4
from firebase_admin import messaging

timers = dict()


def send_notification(tokens, data):
    if len(tokens) == 1:
        message = messaging.Message(data=data, token=tokens[0])
        messaging.send(message)
    else:
        messages = messaging.MulticastMessage(data=data, tokens=tokens)
        messaging.send_multicast(messages)


def add_scheduled_notification(time, tokens, data):
    id = str(uuid4())
    time = parser.parse(time) - datetime.now()
    timers[id] = Timer(time, send_notification, args=(tokens, data))

    return id


def add_medical_notifications(time, tokens, data):
    ids = list()
    time_periods = [270, 180, 1]

    appointment_time = parser.parse(time)
    for i in range(3):
        id = str(uuid4())
        ids.append(id)
        time = (
            appointment_time
            - datetime.now()
            + datetime.timedelta(days=time_periods[i])
        )

        timers[id] = Timer(time, send_notification, args=(tokens, data))

    return ids


def cancel_scheduled_notification(id):
    if id in timers:
        timers[id].cancel()
        del timers[id]