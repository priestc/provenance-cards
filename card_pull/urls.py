from django.urls import path
from .views import (
     index_ui, register_pulls, luck_rank
)

urlpatterns = [
    path('new_box/<int:product_id>', index_ui),
    path('new_box/<int:product_id>/<str:youtube_identifier>', index_ui),
    path('register', register_pulls),
    path("luck_rank/<int:product_id>", luck_rank),
]
