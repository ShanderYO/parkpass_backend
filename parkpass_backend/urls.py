"""parkpass_backend URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static

from base.views import GetAppUrlView
from parkpass_backend import settings
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from fcm_django.api.rest_framework import FCMDeviceAuthorizedViewSet


urlpatterns = [
    path('api/admin/', admin.site.urls),
    #path('admin_tools/', include('admin_tools.urls')),
    path('api/v1/', include('base.urls')),
    path('api/v1/account/', include("accounts.urls")),
    path('api/v1/account/devices/', include("notifications.urls")),
    path('api/v1/payments/', include("payments.urls")),
    path('api/v1/parking/', include("parkings.urls")),
    path('api/v1/partner/', include("partners.urls")),
    path('api/v1/control/', include("control.urls")),
    path('api/v1/owner/', include("owners.urls")),
    path('api/v1/parking/', include("rps_vendor.urls")),
    path('api/v1/vendor/', include("vendors.urls")),
    path('api/v1/auth/', include("jwtauth.urls")),
    path('app/', GetAppUrlView.as_view())

              ] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) \
    + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


urlpatterns += staticfiles_urlpatterns()
