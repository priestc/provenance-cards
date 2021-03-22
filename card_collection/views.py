import json

from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt

from card_set.models import Card, Subset, Set
from .models import CollectionCard

def collection_overview(request, username):
    collection = CollectionCard.objects.filter(owner__username=username)
    card_count = collection.count()
    sets = Set.objects.filter(subset__card__collectioncard__owner__username=username).distinct()
    return render(request, "collection_overview.html", locals())

def set_overview(request, set_id, username):
    set = Set.objects.get(id=set_id)
    subsets = Subset.objects.filter(card__collectioncard__owner__username=username, card__subset__set=set).distinct()
    boxes_of_scarcity = CollectionCard.boxes_of_scarcity_for_user(username, set)
    return render(request, "set_collection.html", locals())

def subset_overview(request, subset_id, username):
    subset = Subset.objects.get(id=subset_id)
    haves = CollectionCard.objects.filter(owner__username=username, card__subset=subset)
    needs = list(Card.objects.filter(subset=subset).exclude(collectioncard__in=haves))
    return render(request, "subset_collection.html", locals())

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
