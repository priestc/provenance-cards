from django.urls import path
from .views import (
    set_overview, subset_overview, register_video,
    card_overview, index_page
)

urlpatterns = [
    path('', index_page),
    path('set_overview/<int:set_id>', set_overview),
    path('subset_overview/<int:subset_id>', subset_overview, name="subset_overview"),
    path('card_overview/<int:subset_id>/<str:slug>', card_overview),
    path('register_video', register_video),
]
