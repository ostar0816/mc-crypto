from django.conf.urls import url
from rest_framework_jwt.views import obtain_jwt_token, refresh_jwt_token, verify_jwt_token

from main.views import api


urlpatterns = [
    url(r'^api/token-auth/', obtain_jwt_token),
    url(r'^api/token-refresh/', refresh_jwt_token),
    url(r'^api/token-verify/', verify_jwt_token),
    url(r'^api/table/(?P<collection>\w+)', api.table, name='table'),

    url(r'^api/top-trades', api.top_trades, name='top_trades'),
]
