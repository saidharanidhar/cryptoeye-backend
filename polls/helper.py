import random
import requests
import time
import os
import logging
from slackclient import SlackClient
from multiprocessing import Process
from django.db.utils import OperationalError
from pytz import timezone

from .models import Currency, NotifyJob

logger = logging.getLogger(__name__)

# Create your views here.

change = float(os.environ.get('INDEX', '2'))
TIME_ZONE = os.environ.get('TIME_ZONE', 'Asia/Kolkata')
ICON = os.environ.get('ICON', ":chart_with_upwards_trend:")
USERNAME = os.environ.get('USERNAME', 'CRYPTOSIGNALS')


def get_data():
    url = 'https://koinex.in/api/ticker'
    data = requests.get(url)
    return data.json()


def calculate(value):
    return ((100 + change) * value) / 100, ((100 - change) * value) / 100


def update_currency(key, value):
    high, low = calculate(value)
    values = dict(value=value, high=high, low=low)
    while True:
        try:
            Currency.objects.update_or_create(coin=key, defaults=values)
            break
        except OperationalError as err:
            time.sleep(random.randint(1, 5))
        except Exception:
            time.sleep(random.randint(1, 5))
            break
    return


def load_currency():
    data = get_data()
    for key in data.get('prices', {}).get('inr').keys():
        value = float(data['prices']['inr'][key])
        Process(target=update_currency, args=(key, value)).start()


def get_emoji(value, low, high):
    if value <= low:
        return ':small_red_triangle_down:'
    return ':arrow_up:'


def get_time(updated):
    parse_tz = timezone(TIME_ZONE)
    return str(updated.astimezone(parse_tz)).split('.')[0]


def send_slack_notification(job, msg):
    sc = SlackClient(job.user.token)
    response = sc.api_call("chat.postMessage", channel=job.user.channel, text=msg, as_user=False, username=USERNAME,
                icon_emoji=ICON)
    logger.info(response)
    del sc


def make_message(key, value, low, high, updated):
    emoji = get_emoji(value, low, high)
    local_time = get_time(updated)
    msg = "*{0}* Treading at Rs *{1}* {2} *{3}%* Last Updated *{4}*".format(key, value, emoji, change, local_time)
    while True:
        try:
            jobs = NotifyJob.objects.filter(coin=key)
            break
        except Exception:
            time.sleep(random.randint(1, 5))
    for job in jobs:
        Process(target=send_slack_notification, args=(job, msg)).start()
        logger.info('jobs started')
        # send_slack_notification(job, msg)


def monitor_currency():
    data = get_data()
    for key in data.get('prices', {}).get('inr').keys():
        value = float(data['prices']['inr'][key])
        while True:
            try:
                coin = Currency.objects.get(coin=key)
                if not coin.low < value < coin.high:
                    Process(target=make_message, args=(key, value, coin.low, coin.high, coin.updated)).start()
                    Process(target=update_currency, args=(key, value)).start()
                break
            except Currency.DoesNotExist:
                load_currency()
                time.sleep(10)
