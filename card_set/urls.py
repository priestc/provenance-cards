from django.urls import path
from .views import (
    set_overview, subset_overview, register_video, index_ui, register_pulls,
    card_overview
)

urlpatterns = [
    path('set_overview/', set_overview),
    path('subset_overview/<int:subset_id>', subset_overview),
    path('card_overview/<int:subset_id>/<str:player_slug>', card_overview),

    path('index_ui/<int:product_id>/', index_ui),
    path('index_ui/<int:product_id>/<str:youtube_identifier>', index_ui),

    path('register_video/', register_video),
    path('register_pulls/', register_pulls),
]
