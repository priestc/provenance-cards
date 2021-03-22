from django.urls import path
from .views import (
    add_to_collection, collection_overview, set_overview, subset_overview
)

urlpatterns = [
    path('enter_subset/<int:subset_id>', add_to_collection),
    path('overview/<str:username>', collection_overview),
    path('set/<int:set_id>/<str:username>', set_overview),
    path('subset/<int:subset_id>/<str:username>', subset_overview)
]
