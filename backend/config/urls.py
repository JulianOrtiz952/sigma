from django.urls import include, path
from hello.views import hello

urlpatterns = [path("api/hello/", hello, name="hello"), path("api/", include("accounts.urls"))]
