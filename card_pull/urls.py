from django.urls import path
from .views import (
     index_ui, register_pulls, luck_rank, breaker_rundown, show_box, edit_box
)

urlpatterns = [
    path('new_box/<int:product_id>', index_ui),
    path('new_box/<int:product_id>/<str:youtube_identifier>', index_ui),
    path('register', register_pulls),
    path("luck_rank/<int:product_id>", luck_rank),
    path("breaker/<int:breaker_id>/product/<int:product_id>", breaker_rundown),
    path("box/<int:box_id>", show_box),
    path("edit_box/<int:box_id>", edit_box),
]
