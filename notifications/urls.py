from django.conf.urls import url

from notifications.views import RegisterAccountDevice, UnregisterAccountDevice

urlpatterns = [
    url(r'^register/$', RegisterAccountDevice.as_view()),
    url(r'^unregister/$', UnregisterAccountDevice.as_view())
]
