from django.urls import path
from .views import set_overview, subset_overview, register_video, index_ui

urlpatterns = [
    path('set_overview/', set_overview),
    path('subset_overview/', subset_overview),
    path('index_ui/<int:product_id>/', index_ui),
    path('register_video/', register_video),
]
