from django.contrib import admin
from django.urls import include, path

handler403 = "polls.views.error_403"
handler404 = "polls.views.error_404"
handler500 = "polls.views.error_500"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),
    path("", include("polls.urls")),
]
