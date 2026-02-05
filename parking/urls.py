from django.urls import path
from .views import find_nearest_parking

app_name = 'parking'

urlpatterns = [
    path('find-nearest/', find_nearest_parking, name='find_nearest_parking'),
]
