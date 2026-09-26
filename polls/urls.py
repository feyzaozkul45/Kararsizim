from django.urls import path

from . import views

urlpatterns = [
    path("", views.poll_list, name="poll_list"),
    path("anket/yeni/", views.poll_create, name="poll_create"),
    path("anket/<int:pk>/", views.poll_detail, name="poll_detail"),
    path("anket/<int:pk>/oy/", views.poll_vote, name="poll_vote"),
    path("anket/<int:pk>/kapat/", views.poll_toggle, name="poll_toggle"),
    path("anket/<int:pk>/sil/", views.poll_delete, name="poll_delete"),
    path("anketlerim/", views.my_polls, name="my_polls"),
]
