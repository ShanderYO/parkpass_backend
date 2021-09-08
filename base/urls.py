from django.conf.urls import url

from base.views import NotifyIssueView, GetCountriesView

urlpatterns = [
    url(r'^notify/$', NotifyIssueView.as_view()),
    url(r'^countries/$', GetCountriesView.as_view())
]
