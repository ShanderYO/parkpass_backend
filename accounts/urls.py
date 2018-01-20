from django.conf.urls import url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from accounts.views import LoginView, LogoutView, AccountView, ConfirmLoginView, CreateCardView, DeleteCardView, SetDefaultCardView

urlpatterns = [
    url(r'^login/$', LoginView.as_view()),
    url(r'^login/confirm/$', ConfirmLoginView.as_view()),
    url(r'^logout/$', LogoutView.as_view()),
    url(r'^me/$', AccountView.as_view()),
    url(r'^card/add/', CreateCardView.as_view()),
    url(r'^card/delete/', DeleteCardView.as_view()),
    url(r'^card/default/', SetDefaultCardView.as_view()),
]

urlpatterns += staticfiles_urlpatterns()