import json

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import Set, Subset, Video, Product

def set_overview(request):
    set_id = request.GET['set']
    set = Set.objects.get(id=set_id)

    subsets = set.all_subsets()
    non_auto_subsets = subsets['Subsets']
    auto_subsets = subsets['Autographs']

    product_overview = set.products_summary()

    return render(
        request, "set_overview.html", locals()
    )

def subset_overview(request):
    id = request.GET['id']
    subset = Subset.objects.get(pk=id)

    statistics = subset.percent_indexed()
    summary = subset.pull_count()

    return render(
        request, "subset_overview.html", locals()
    )

def index_ui(request, product_id):
    product = Product.objects.get(id=product_id)
    dropdowns = product.set.get_subset_dropdowns()
    shorthands_json = json.dumps(product.set.get_shorthands())
    players = product.set.get_player_list()
    expected_pulls = 12
    return render(request, "index_ui.html", locals())

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
