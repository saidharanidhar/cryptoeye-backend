from django.contrib.auth.models import User
from django.db import models

# Create your models here.
from django.utils import timezone


class UserProfile(models.Model):
    user_details = models.OneToOneField(User, related_name='user_detail', on_delete=models.CASCADE)
    token = models.CharField(max_length=1024)
    channel = models.CharField(max_length=15)

    def __str__(self):
        return "{0}".format(self.user_details)


class Currency(models.Model):
    coin = models.CharField(max_length=20, primary_key=True)
    value = models.DecimalField(max_digits=13, decimal_places=3)
    high = models.DecimalField(max_digits=13, decimal_places=3)
    low = models.DecimalField(max_digits=13, decimal_places=3)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "{0}- V {1}- H {2}- L {3}".format(self.coin, self.value, self.high, self.low)


class NotifyJob(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    coin = models.ForeignKey(Currency, db_column='coin', on_delete=models.DO_NOTHING)

    class Meta:
        unique_together = (("user", "coin"),)

    def __str__(self):
        return "{0} - {1}".format(self.user, self.coin)



