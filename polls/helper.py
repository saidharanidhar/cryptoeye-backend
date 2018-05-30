import decimal
import random
import requests
import time
import os
import logging

from django.utils import timezone as dj_timezone
from django.utils.timesince import timesince
from django.db.utils import OperationalError
from django.db import transaction as db_transaction
from multiprocessing import Process
from slackclient import SlackClient
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
    with db_transaction.atomic():
        Currency.objects.select_for_update().update_or_create(coin=key, defaults=values)
    # while True:
    #     try:
    #         Currency.objects.update_or_create(coin=key, defaults=values)
    #         break
    #     except OperationalError as err:
    #         print(key, err)
    #         time.sleep(random.randint(1, 5))
    #     except Exception as err:
    #         print(key, err)
    #         time.sleep(random.randint(1, 5))
    #         break
    return


def load_currency():
    data = get_data()
    for key in data.get('prices', {}).get('inr').keys():
        value = float(data['prices']['inr'][key])
        # Process(target=update_currency, args=(key, value)).start()
        update_currency(key, value)


def get_emoji(value, low, high, previous):
    if value <= low:
        return ':small_red_triangle_down:', round(100 - ((decimal.Decimal(value)*100)/previous), 2)
    return ':arrow_up:', round((decimal.Decimal(value)*100)/previous - 100, 2)


def get_time(updated):
    parse_tz = timezone(TIME_ZONE)
    return str(updated.astimezone(parse_tz)).split('.')[0]


def send_slack_notification(job, msg):
    sc = SlackClient(job.user.token)
    response = sc.api_call("chat.postMessage", channel=job.user.channel, text=msg, as_user=False, username=USERNAME,
                           icon_emoji=ICON)
    # logger.info(response)
    del sc
    del response


def make_message(key, value, low, high, previous, updated, present_time):
    diff = timesince(updated, present_time)
    emoji, percent = get_emoji(value, low, high, previous)
    # local_time = get_time(updated)
    msg = "*{0}* Treading at Rs *{1}*, *{2}%* {3} in *{4}*, Previously Rs *{5}*".format(
        key, value, percent, emoji, diff, previous )

    jobs = NotifyJob.objects.select_related().filter(coin=key)
    # with db_transaction.atomic():
    #     jobs = NotifyJob.objects.select_for_update().select_related().filter(coin=key)
    # while True:
    #     try:
    #         jobs = NotifyJob.objects.select_related('coin__coin','user__token','user__channel').filter(coin=key)
    #         break
    #     except Exception as err:
    #         print('mm', err)
    #         time.sleep(random.randint(1, 5))
    for job in jobs:
        # Process(target=send_slack_notification, args=(job, msg)).start()
        send_slack_notification(job, msg)
        # logger.info('jobs started')
        # send_slack_notification(job, msg)


def monitor_currency():
    data = get_data()
    present_time = dj_timezone.now()
    for key in data.get('prices', {}).get('inr').keys():
        value = float(data['prices']['inr'][key])
        with db_transaction.atomic():
            coin = Currency.objects.select_for_update().get(coin=key)
        if not coin.low < value < coin.high:
            # Process(target=make_message, args=(key, value, coin.low, coin.high, coin.updated)).start()
            make_message(key, value, coin.low, coin.high, coin.value, coin.updated, present_time)
            # Process(target=update_currency, args=(key, value)).start()
            update_currency(key, value)

            # while True:
            #     try:
            #         coin = Currency.objects.get(coin=key)
            #         if not coin.low < value < coin.high:
            #             # Process(target=make_message, args=(key, value, coin.low, coin.high, coin.updated)).start()
            #             make_message(key, value, coin.low, coin.high, coin.updated)
            #             # Process(target=update_currency, args=(key, value)).start()
            #             update_currency(key, value)
            #         break
            #     except Currency.DoesNotExist as err:
            #         print(key, err)
            #         load_currency()
            #         time.sleep(10)
