# detail_project/tests/urls_stub.py
from django.http import HttpResponse
from django.urls import path

# Stub views (cukup return 200 "ok")
def ok(_): return HttpResponse("ok")

app_name = "detail_project"

urlpatterns = [
    # dashboard namespace
    path("dashboard/", ok, name="dashboard"),
    # detail_project namespace (names used in templates)
    path("list/", ok, name="list_pekerjaan"),
    path("volume/", ok, name="volume_pekerjaan"),
    path("harga/", ok, name="harga_items"),
    path("detail/", ok, name="detail_ahsp"),
    path("detail-gabungan/", ok, name="detail_ahsp_gabungan"),
    path("rekap/", ok, name="rekap_rab"),
]
