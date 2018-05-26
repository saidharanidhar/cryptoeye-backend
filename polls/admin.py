from django.contrib import admin
from .models import Currency, NotifyJob, UserProfile
# Register your models here.


class ReadonlyFields(admin.ModelAdmin):
    readonly_fields = ('updated',)


admin.site.register(Currency, ReadonlyFields)
admin.site.register(NotifyJob)
admin.site.register(UserProfile)