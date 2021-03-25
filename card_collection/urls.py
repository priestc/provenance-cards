from django.urls import path
from .views import (
    add_to_collection, collection_overview, set_overview, subset_overview,
    by_subject, collection_subject_list
)

urlpatterns = [
    path('enter_subset/<int:subset_id>', add_to_collection),

    path('<str:username>', collection_overview),
    path('<str:username>/by_subject', collection_subject_list),
    path('<str:username>/by_subject/<str:subject_slug>', by_subject),

    path('<str:username>/set/<int:set_id>', set_overview),
    path('<str:username>/set/<int:set_id>/by_subject', collection_subject_list),
    path('<str:username>/set/<int:set_id>/by_subject/<str:subject_slug>', by_subject),

    path('<str:username>/subset/<int:subset_id>/', subset_overview)
]
