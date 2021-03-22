from django.urls import path
from .views import (
    add_to_collection, collection_overview
)

urlpatterns = [
    path('enter_subset/<int:subset_id>', add_to_collection),
    path('overview/<str:username>', collection_overview)
]
