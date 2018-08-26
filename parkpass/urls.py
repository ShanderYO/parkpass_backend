"""parkpass URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.8/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from parkpass import settings

urlpatterns = [
    url(r'^admin_tools/', include('admin_tools.urls')),
    url(r'^api/admin/', include(admin.site.urls)),
    url(r'^api/v1/account/', include("accounts.urls")),
    url(r'^api/v1/parking/', include("parkings.urls")),
    url(r'^api/v1/payments/', include("payments.urls")),
                  url(r'^api/v1/control/', include("control.urls")),
                  url(r'^api/v1/owner/', include("owners.urls")),
    # Vendor extensions

    url(r'^api/v1/parking/', include("rps_vendor.urls")),
    url(r'^api/v1/vendor/', include("vendors.urls"))
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) \
              + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += staticfiles_urlpatterns()
