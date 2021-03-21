from django.urls import path
from .views import (
    add_to_collection
)

urlpatterns = [
    path('enter_subset/<int:subset_id>', add_to_collection),
]
