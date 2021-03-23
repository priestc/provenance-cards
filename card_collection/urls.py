from django.urls import path
from .views import (
    add_to_collection, collection_overview, set_overview, subset_overview,
    set_by_subject, collection_by_subject, collection_subject_list
)

urlpatterns = [
    path('enter_subset/<int:subset_id>', add_to_collection),

    path('<str:username>', collection_overview),
    path('<str:username>/by_subject', collection_subject_list),
    path('<str:username>/<str:subject>', collection_by_subject),

    path('<str:username>/set/<int:set_id>', set_overview),
    path('<str:username>/set/<int:set_id>/<str:subject>', set_by_subject),

    path('<str:username>/subset/<int:subset_id>/', subset_overview)
]
