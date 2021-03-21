import json

from django.shortcuts import render
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt

from .models import Set, Subset, Video, Product, Pull, Box, Subject, Card, clean_color

def set_overview(request):
    set_id = request.GET['set']
    set = Set.objects.get(id=set_id)

    subsets = set.all_subsets(categories=True)
    non_auto_subsets = subsets['Subsets']
    auto_subsets = subsets['Autographs']

    product_overview = set.products_summary()

    return render(request, "set_overview.html", locals())

def subset_overview(request, subset_id):
    subset = Subset.objects.get(pk=subset_id)

    statistics = subset.percent_indexed()

    if subset.multi_base_numbered:
        summary = subset.multibase_numbered_pull_count()
    else:
        summary = subset.pull_count()

    if subset.multi_base or subset.multi_base_numbered:
        unique = len([k for k,v in summary.items() if v['count'] > 0])
    else:
        unique = len([k for k,v in summary.items() if v > 0])
    if subset.checklist_size:
        unique_percent = unique / subset.checklist_size * 100

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
def luck_rank(request, product_id):
    scarcity_score = request.POST['scarcity_score']
    direction = request.POST['direction']
    return JsonResponse({
        "rank": Product.potential_rank(product_id, scarcity_score, direction)
    })

@csrf_exempt
def index_ui(request, product_id, youtube_identifier=None):
    product = Product.objects.get(id=product_id)

    if request.POST:
        youtube_id = request.POST['youtube_id']
        try:
            details = Video.get_youtube_info(youtube_id)
        except Exception as exc:
            error = "Invalid youtube url"
            return render(request, "index_ui.html", locals())

        video, c = Video.objects.get_or_create(**details)
        return HttpResponseRedirect(
            "/index_ui/%s/%s" % (product.id, details['youtube_identifier'])
        )

    if youtube_identifier:
        video = Video.objects.get(youtube_identifier=youtube_identifier)
        luck_ranges = product.get_luck_ranges()
        dropdowns = product.set.get_subset_dropdowns()
        shorthands_json = json.dumps(product.set.get_shorthands())
        subjects = product.set.get_subject_list()
        expected_pulls = product.set.cards_per_box()
        next_order = video.box_set.count() + 1
        left_off = video.last_pull_timestamp()
        multi_base_numbered = Subset.objects.filter(set__product=product, multi_base_numbered=True)

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


def get_subset_id(subset_name, color, subsets):
    subset_colors = subsets[subset_name]

    cleaned_color, serial_base = clean_color(color)
    for subset_color in subset_colors:
        if subset_color['color'] == cleaned_color:
            if 'multi_base_numbered' in subset_color:
                return subset_color['id'], serial_base
            if serial_base == subset_color['serial_base']:
                return subset_color['id']

    return None

@csrf_exempt
def register_pulls(request):
    product = Product.objects.get(id=request.POST['product_id'])
    pulls = json.loads(request.POST['pulls'])
    video = Video.objects.get(youtube_identifier=request.POST['video_id'])
    box_order = request.POST['order']
    subsets = product.set.all_subsets()
    box = Box.objects.create(video=video, order=box_order, product=product)

    for pull in pulls:
        if pull['subset_name'] == '---':
            continue

        new_pulls = []
        subset_id = get_subset_id(pull['subset_name'], pull['color'], subsets)
        try:
            new_pulls.append(Pull.objects.create(
                box=box, card=Card.get_card(subset_id, pull, product.set), serial=pull['serial'],
                front_timestamp=pull['front_timestamp'], damage=pull['damage'],
                back_timestamp=pull['back_timestamp'] or None
            ))
        except:
            for new_pull in new_pulls:
                new_pull.delete()
            box.delete()
            raise

    box.calculate_scarcity_score()
    return HttpResponse("OK")
