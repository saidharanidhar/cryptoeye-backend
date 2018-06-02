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
USERNAME = os.environ.get('USERNAME', 'CryptoSignals')


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
    return


def load_currency():
    data = get_data()
    for key in data.get('prices', {}).get('inr').keys():
        value = float(data['prices']['inr'][key])
        # Process(target=update_currency, args=(key, value)).start()
        update_currency(key, value)


def get_emoji(value, low, high, previous):
    if value <= low:
        return ':small_red_triangle_down:', round(100 - ((decimal.Decimal(value) * 100) / previous), 2)
    return ':arrow_up:', round((decimal.Decimal(value) * 100) / previous - 100, 2)


def get_time(updated):
    parse_tz = timezone(TIME_ZONE)
    return updated.astimezone(parse_tz)


def send_slack_notification(job, msg):
    sc = SlackClient(job.user.token)
    response = sc.api_call("chat.postMessage", channel=job.user.channel, text=msg, as_user=False, username=USERNAME,
                           icon_emoji=ICON)
    del sc
    del response


def decide_change(change_of):
    state = 'No change'
    if change_of < 0:
        state = 'Loss of'
    if change_of > 0:
        state = 'Profit of'

    return state, round(abs(change_of), 3)


def profit_or_loss(job, value, present_time):
    if not job.investment:
        return ''
    change_of = job.investment * ((decimal.Decimal(value) - job.coin_value) / job.coin_value)
    state, change_of = decide_change(change_of)
    in_time = timesince(get_time(job.on_time), present_time)
    statement = "`{0} Rs {1} in {2} Invested Rs {3} at Rs {4}`\n".format(state, change_of, in_time, job.investment,
                                                                         job.coin_value)
    return statement


def make_message(key, value, low, high, previous, updated, present_time, buy, sell):
    diff = timesince(updated, present_time)
    emoji, percent = get_emoji(value, low, high, previous)

    msg = "*{0}* Treading at Rs *{1}*, *{2}%* {3} in *{4}*, Previously Rs *{5}*  \n".format(
        key, value, percent, emoji, diff, previous)
    trade_stats = "`Buyers from Rs {0} Sellers from Rs {1}`\n".format(buy, sell)

    jobs = NotifyJob.objects.select_related().filter(coin=key)
    for job in jobs:
        job_msg = msg + profit_or_loss(job, buy, present_time) + trade_stats
        send_slack_notification(job, job_msg)
        # Process(target=send_slack_notification, args=(job, job_ssssmsg)).start()


def get_value(data, key):
    return (
        float(data['prices']['inr'][key]),
        float(data['stats']['inr'][key]['highest_bid']),
        float(data['stats']['inr'][key]['lowest_ask'])
    )


def monitor_currency():
    data = get_data()
    present_time = dj_timezone.now()
    for key in data.get('prices', {}).get('inr').keys():
        value, buy, sell = get_value(data, key)
        with db_transaction.atomic():
            coin = Currency.objects.select_for_update().get(coin=key)
        if not coin.low < value < coin.high:
            make_message(key, value, coin.low, coin.high, coin.value, coin.updated, present_time, buy, sell)
            update_currency(key, value)
            # Process(target=make_message, args=(key, value, coin.low, coin.high, coin.updated)).start()
            # Process(target=update_currency, args=(key, value)).start()
