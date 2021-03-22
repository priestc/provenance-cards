import json

from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt

from card_set.models import Card, Subset
from .models import CollectionCard

@csrf_exempt
def add_to_collection(request, subset_id):
    subset = Subset.objects.get(pk=subset_id)
    subjects = subset.set.get_subject_list()

    if not request.POST:
        return render(request, "collection_add.html", locals())

    for item in json.loads(request.POST['cards']):
        if not item['subject']:
            break
        CollectionCard.objects.create(
            card=Card.get_card(subset_id, item, subset.set),
            serial=item['serial'], damage=item['damage'], owner=request.user
        )

    return redirect('subset_overview', subset_id=subset_id)
