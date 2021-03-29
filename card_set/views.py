from django.shortcuts import render
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt

from .models import Set, Subset, Video, Product, Subject, Card


def set_overview(request, set_id):
    set = Set.objects.get(id=set_id)

    subsets = set.all_subsets(categories=True)
    non_auto_subsets = subsets['Subsets']
    auto_subsets = subsets['Autographs']

    product_overview = set.products_summary()

    return render(request, "set_overview.html", locals())

def subset_overview(request, subset_id):
    subset = Subset.objects.get(pk=subset_id)
    statistics = subset.percent_indexed()
    pull_items = Card.objects.filter(subset=subset)
    return render(
        request, "subset_overview.html", locals()
    )

def card_overview(request, subset_id, slug):
    subset = Subset.objects.get(pk=subset_id)
    subject = Subject.objects.get(slug=slug)

    pulls = subset.pulls_for_subject(subject)

    return render(
        request, "card_overview.html", locals()
    )

############### api endpoints below

@csrf_exempt
def register_video(request):
    youtube_id = request.POST['youtube_id']
    try:
        details = Video.get_youtube_info(youtube_id)
    except Exception as exc:
        return JsonResponse({"error": str(exc)})

    video, c = Video.objects.get_or_create(**details)
    return JsonResponse({
        "video_id": video.id, "created": c, "next_index": video.next_index()
    })
