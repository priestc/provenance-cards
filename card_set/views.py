import json

from django.shortcuts import render
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt

from .models import Set, Subset, Video, Product, Pull, Box, Player

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
    summary = subset.pull_count()

    unique = len(summary.keys())
    if subset.checklist_size:
        unique_percent = unique / subset.checklist_size * 100

    return render(
        request, "subset_overview.html", locals()
    )

def card_overview(request, subset_id, player_slug):
    subset = Subset.objects.get(pk=subset_id)
    player = Player.objects.get(player_slug=player_slug)

    pulls = subset.pulls_for_player(player)

    return render(
        request, "card_overview.html", locals()
    )

############### api endpoints below

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
        luck_ranges = product.set.get_luck_ranges()
        dropdowns = product.set.get_subset_dropdowns()
        shorthands_json = json.dumps(product.set.get_shorthands())
        players = product.set.get_player_list()
        expected_pulls = product.set.cards_per_box()
        next_order = video.box_set.count() + 1
        left_off = video.last_pull_timestamp()

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
        player, c = Player.objects.get_or_create(player_name=pull['player_name'])

        subset_id = get_subset_id(pull['subset_name'], pull['color'], subsets)
        if not subset_id:
            cleaned_color, serial_base = clean_color(pull['color'])
            subset = Subset.objects.create(
                set=product.set, serial_base=serial_base, name=pull['subset_name'],
                color=cleaned_color
            )
        else:
            subset = Subset.objects.get(id=subset_id)

        Pull.objects.create(
            box=box, subset=subset, serial=pull['serial'], player=player,
            front_timestamp=pull['front_timestamp'], damage=pull['damage'],
            back_timestamp=pull['back_timestamp'] or None
        )

    box.calculate_scarcity_score()
    return HttpResponse("OK")

def get_subset_id(subset_name, color, subsets):
    subset_colors = subsets[subset_name]

    cleaned_color, serial_base = clean_color(color)
    for subset_color in subset_colors:
        if subset_color['color'] == cleaned_color and serial_base == subset_color['serial_base']:
            return subset_color['id']

    return None

def clean_color(color):
    if "Unnumbered" in color:
        serial_base = None
        pre_serial = color[:-10]
    elif "/" in color:
        pre_serial, serial_base = color.split("/")
        serial_base = int(serial_base)

    cleaned_color = pre_serial.strip()
    return cleaned_color, serial_base
