from django.conf.urls.defaults import *
from nearby import views

urlpatterns = patterns('',
    ('^$', views.index),
    ('^auth/$', views.auth),
    ('^return/$', views.return_),
    ('^nearby/$', views.nearby),
    ('^unauth/$', views.unauth),
)
