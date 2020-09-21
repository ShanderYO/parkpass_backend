import json

from django.contrib import admin
from django import forms

# Register your models here.
from notifications.models import AccountDevice
from notifications.tasks import send_broadcast_message


class PushWidgetForm(forms.ModelForm):

    groups_keys = [
        "title", "body", "data"
    ]

    title = forms.CharField(required=False, max_length=255)
    body = forms.CharField(required=False, max_length=1024, widget=forms.Textarea())
    data = forms.CharField(required=False, max_length=10000, widget=forms.Textarea())
    is_broadcast = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        if 'initial' not in kwargs:
            kwargs['initial'] = {}
        super(PushWidgetForm, self).__init__(*args, **kwargs)

    def processData(self, input):
        return input + " has been processed"

    def save(self, commit=True):
        title = self.cleaned_data.get("title", None)
        body = self.cleaned_data.get("body", None)
        data = self.cleaned_data.get("data", None)

        instance = super(PushWidgetForm, self).save(commit=commit)
        if commit:
            instance.save()

        if self.cleaned_data.get("is_broadcast", None):
            send_broadcast_message.apply_async((title, body, data))
            return instance

        if title and body:
            if data:
                d = json.loads(data)
                instance.send_message(title=title, body=body, data=d)
            else:
                instance.send_message(title=title, body=body)
        return instance

    class Meta:
        model = AccountDevice
        fields = ('account', 'type', 'active', 'registration_id', 'device_id',)


@admin.register(AccountDevice)
class AccountDeviceAdmin(admin.ModelAdmin):
    form = PushWidgetForm

    search_fields = ('account',)

    list_display = ('account', 'type', 'active',)

    readonly_fields = ('type',)

    exclude_fields = ('user', 'name',)
