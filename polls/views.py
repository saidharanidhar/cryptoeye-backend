from django.http import HttpResponse
from multiprocessing import Process
from .helper import monitor_currency, load_currency


def healthcheck(request):
    return HttpResponse('Ok', status=200)


def hot_load(request):
    Process(target=monitor_currency).start()
    # monitor_currency()
    return HttpResponse('Ok', status=200)


def factory_load(request):
    Process(target=load_currency).start()
    # load_currency()
    return HttpResponse('Ok', status=200)
