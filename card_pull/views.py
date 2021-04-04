import json

from django.shortcuts import render
from django.utils import timezone
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt

from .models import Box, Pull
from card_set.models import Product, Video, Subset, Card, clean_color, Breaker

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

def new_pull_from_form(box, subsets, pull):
    subset_id = get_subset_id(pull['subset_name'], pull['color'], subsets)
    return Pull.objects.create(
        box=box, card=Card.get_card(subset_id, pull, box.product.set), serial=pull['serial'],
        front_timestamp=pull['front_timestamp'], damage=pull['damage'],
        back_timestamp=pull['back_timestamp'] or None
    )

@csrf_exempt
def register_pulls(request):
    product = Product.objects.get(id=request.POST['product_id'])
    pulls = json.loads(request.POST['pulls'])
    video = Video.objects.get(youtube_identifier=request.POST['video_id'])
    box_order = request.POST['order']
    subsets = product.set.all_subsets()
    box = Box.objects.create(video=video, order=box_order, product=product)

    new_pulls = []
    for pull in pulls:
        if pull['subset_name'] == '---':
            continue
        try:
            new_pulls.append(new_pull_from_form(box, subsets, pull))
        except:
            for new_pull in new_pulls:
                new_pull.delete()
            box.delete()
            raise

    box.indexed_by = request.user
    box_indexed_on = timezone.now()
    box.calculate_scarcity_score()
    return HttpResponse("OK")

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
            "/pulls/new_box/%s/%s" % (product.id, details['youtube_identifier'])
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
def luck_rank(request, product_id):
    scarcity_score = request.POST['scarcity_score']
    direction = request.POST['direction']
    return JsonResponse({
        "rank": Product.potential_rank(product_id, scarcity_score, direction)
    })


def breaker_rundown(request, breaker_id, product_id):
    breaker = Breaker.objects.get(pk=breaker_id)
    product = Product.objects.get(pk=product_id)
    breaker.calc_stats_for_product(product)
    return render(request, "breaker_product.html", locals())

def show_box(request, box_id):
    box = Box.objects.get(pk=box_id)
    return render(request, "show_box.html", locals())

@csrf_exempt
def edit_box(request, box_id):
    existing_box = Box.objects.get(pk=box_id)
    product = existing_box.product

    if not request.POST:
        youtube_identifier = existing_box.video.youtube_identifier
        product_id = product.id
        next_order = existing_box.order
        left_off = existing_box.start_timestamp() - 5
        dropdowns = product.set.get_subset_dropdowns()
        shorthands_json = json.dumps(product.set.get_shorthands())
        subjects = product.set.get_subject_list()
        multi_base_numbered = Subset.objects.filter(set__product=product, multi_base_numbered=True)
        existing_pulls = existing_box.pull_set.order_by('front_timestamp')
    else:
        updated_pull_data = json.loads(request.POST['pulls'])
        subsets = product.set.all_subsets()
        existing_pulls = list(Pull.objects.filter(box=existing_box).order_by('front_timestamp'))

        for i, pull in enumerate(updated_pull_data):
            if pull['subset_name'] == '---':
                continue
            try:
                existing_pull = existing_pulls[i]
            except IndexError:
                new_pull_from_form(existing_box, subsets, pull)
                print(i, "new card", pull)
                continue

            print(i, "before", existing_pull)

            subset_id = get_subset_id(pull['subset_name'], pull['color'], subsets)

            existing_pull.card = Card.get_card(subset_id, pull, product.set)
            existing_pull.serial = pull['serial']
            existing_pull.front_timestamp = pull['front_timestamp'] or 0
            existing_pull.back_timestamp = pull['back_timestamp'] or None
            existing_pull.damage = pull['damage']

            print(i, "saving", pull, "to", existing_pull)
            existing_pull.save()
            print(i, "after", existing_pull)
            print("------------------------------------")

        return HttpResponse("OK")


    return render(request, "index_ui.html", locals())
