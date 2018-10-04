from django.conf.urls import url

from base.views import NotifyIssueView

urlpatterns = [
    url(r'^notify/$', NotifyIssueView.as_view())
]
