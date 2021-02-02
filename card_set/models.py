import collections
import datetime
import json

from django.db import models

from youtubesearchpython import Video as YTVideo, ResultMode

def verbose_color(serial_base, color):
    sb = ("/%s" % serial_base) if serial_base else "Unnumbered"
    if not color:
        return sb
    return "%s %s" % (color, sb)

# Create your models here.
class Set(models.Model):
    year = models.IntegerField()
    name = models.TextField()
    manufacturer = models.ForeignKey('Manufacturer', on_delete=models.PROTECT)

    def __str__(self):
        return "%s %s %s" % (self.year, self.manufacturer, self.name)

    def products_summary(self):
        stats = {}
        total = 0
        for prod in self.product_set.all():
            count = prod.box_set.count()
            stats[prod] = count
            total += count

        detailed_stats = {}
        for prod, count in stats.items():
            detailed_stats[prod] = {'count': count, 'percent': 100 * count/total}

        return detailed_stats

    def cards_per_box(self):
        avgs = []
        all_subsets = Subset.objects.filter(set=self)
        all_pulls = Video.objects.filter(subset__in=all_subsets)
        for vid in all_pulls:
            avgs.append(vid.cards_per_box())

        return sum(avgs) / len(avgs)

    def all_subsets(self, for_dropdown=False):
        subsets = collections.defaultdict(list)
        autographs = collections.defaultdict(list)

        for subset in self.subset_set.values('name', 'color', 'serial_base', 'id', 'checklist_size'):
            color = subset['color']
            serial_base = subset['serial_base']
            name = subset['name']

            if "Auto" in name:
                section = autographs
            else:
                section = subsets

            if subset['checklist_size'] and serial_base:
                population = -1 * int(subset['checklist_size']) * int(serial_base)
            else:
                population = 0

            section[name].append({
                "color": color, "serial_base": serial_base, 'id': subset['id'],
                "pop": population
            })

        return {
            'Autographs': dict(autographs), "Subsets": dict(subsets)
        }

    def get_subset_dropdowns(self):
        subsets = self.all_subsets()
        subsets_no_categories = {**subsets['Subsets'], **subsets['Autographs']}
        menus = collections.defaultdict(list)
        for name, kinds in subsets_no_categories.items():
            accumulated_pop = 0
            for data in kinds:
                if data['serial_base']:
                    sort = str(1 * data['serial_base']).zfill(5)
                else:
                    sort = "999999999999" + data['color']
                menus['color'].append([
                    verbose_color(data['serial_base'], data['color']), sort
                ])
                accumulated_pop += data['pop']

            menus['name'].append([name, accumulated_pop])

        menus['name'] = sorted(menus['name'], key=lambda x: x[1])

        c = {x[0]: x[1] for x in menus['color']} # removing duplicates
        menus['color'] = sorted(c.items(), key=lambda x: x[1], reverse=True)

        return menus

    def get_shorthands(self):
        mapping = {}
        for subset in self.subset_set.all():
            if subset.shorthand:
                mapping[subset.shorthand] = [subset.name, subset.verbose_color()]
        return mapping

    def get_player_list(self):
        all_pulls = Pull.objects.filter(box__product__set=self)
        return list(
            Player.objects.filter(pull__in=all_pulls).values_list('player_name', flat=True).distinct()
        )

class Manufacturer(models.Model):
    manufacturer = models.TextField()
    mlb_licensed = models.BooleanField()

    def __str__(self):
        return self.manufacturer

class Subset(models.Model):
    color = models.TextField(blank=True)
    serial_base = models.IntegerField(null=True, blank=True)
    name = models.TextField()
    set = models.ForeignKey("Set", on_delete=models.PROTECT)
    checklist_size = models.IntegerField(blank=True, null=True)
    shorthand = models.CharField(max_length=16, blank=True)

    def __str__(self):
        return "%s %s (%s)" % (self.set, self.name, self.verbose_color())

    def verbose_color(self):
        return verbose_color(self.serial_base, self.color)

    def total_population(self):
        return (
            self.checklist_size * self.serial_base
            if self.checklist_size and self.serial_base
            else None
        )

    def percent_indexed(self):
        indexed = {}
        for product, counts in self.set.products_summary().items():
            product_pop = counts['count']
            data = self.find_from_product(product)
            found = data['total_found'].count()
            expected = self.total_population() or None
            matched = len(set(data['matched_boxes']))
            odds = found / float(product_pop)
            percent = 100 * found / float(expected) if expected else None
            if found == 0:
                display_odds = None
            else:
                display_odds = "1:%.1f" % (1/odds) if odds < 1 else "%.1f:1" % (odds)
            indexed[product] = {
                'found': found,
                'boxes_found_in': matched,
                'box_population': product_pop,
                'expected': expected,
                'percentage_found': percent,
                'odds_per_box': display_odds
            }
        return indexed

    def estimate_set_size(self):
        if not self.serial_base:
            return

        total_pop = self.total_population()
        if not total_pop:
            return
        estimates = {}
        for product, data in self.percent_indexed().items():
            boxes_indexed = data['box_population']
            percent = data['percentage_found'] / 100.0
            found = data['found']
            if percent == 0:
                estimates[product] = None
            else:
                estimates[product] = boxes_indexed / percent
        return estimates


    def find_from_product(self, product):
        pulls = Pull.objects.filter(box__product=product, subset=self).order_by('player')
        return {
            'matched_boxes': [p.box for p in pulls],
            'total_found': pulls
        }

    def pull_count(self):
        summary = collections.defaultdict(lambda: 0)
        for pull in Pull.objects.filter(subset=self).values('player__player_name'):
            summary[pull['player__player_name']] += 1

        return dict(summary)

    def seen_checklist_size(self):
        return Pull.objects.filter(subset=self).values("player").distinct().count()

    def seen_percentage(self):
        if not self.serial_base:
            return
        return 100.0 * self.seen_checklist_size() / self.checklist_size

    class Meta:
        ordering = ("-serial_base", )

class Player(models.Model):
    player_name = models.TextField()
    variation = models.TextField(blank=True)

    def __str__(self):
        return "%s %s" % (self.player_name, self.variation)

    class Meta:
        ordering = ('player_name', )

class Video(models.Model):
    youtube_identifier = models.TextField(unique=True)
    breaker = models.ForeignKey("Breaker", on_delete=models.PROTECT)
    comment = models.TextField(blank=True)
    date = models.DateTimeField(null=True)

    @classmethod
    def get_youtube_info(cls, youtube_identifier):
        try:
            info = json.loads(
                YTVideo.getInfo('https://youtu.be/%s' % youtube_identifier, mode=ResultMode.json)
            )
        except TypeError:
            raise Exception("Invalid youtube video id")

        breaker, c = Breaker.objects.get_or_create(name=info['channel']['name'])
        date = info['publishDate']

        return {
            'youtube_identifier': youtube_identifier,
            "breaker": breaker,
            "date": datetime.datetime.strptime(date, "%Y-%m-%d")
        }


    def update_info(self):
        if self.date:
            return
        info = Video.get_youtube_info(self.youtube_identifier)
        self.date = info['date']
        self.save()

    def boxes(self):
        return self.box_set.count()

    def __str__(self):
        return "%s %s" % (self.youtube_identifier, self.breaker)

    def cards_per_box(self):
        return self.pull_set.count() / self.boxes

    def pulls_recorded(self):
        count = 0
        for box in self.box_set.all():
            count += box.pull_set.count()
        return count

    def display_boxes(self):
        disp = ""
        for b in self.box_set.order_by('order'):
            disp += "Box %s \n%s\n\n" % (b.order, b.display())
        return disp

    def next_index(self):
        try:
            return self.box_set.order_by("-order")[0].order + 1
        except IndexError:
            return 1

class Breaker(models.Model):
    name = models.TextField()

    def __str__(self):
        return self.name

class Pull(models.Model):
    subset = models.ForeignKey("Subset", on_delete=models.PROTECT)
    serial = models.TextField(blank=True)
    player = models.ForeignKey("Player", on_delete=models.PROTECT)
    timestamp = models.TextField(blank=True)
    damage = models.TextField(blank=True)
    box = models.ForeignKey("Box", on_delete=models.PROTECT, null=True)

    def __str__(self):
        if self.subset.serial_base and not self.serial:
            serial = "?/%s" % self.subset.serial_base
        elif self.serial:
            serial = "%s/%s" % (self.serial, self.subset.serial_base)
        else:
            serial = "Unnumbered"

        return "%s %s %s %s" % (self.player, self.subset.name, self.subset.color, serial)

class Product(models.Model):
    set = models.ForeignKey("Set", on_delete=models.PROTECT)
    type = models.TextField()
    packs_per_box = models.IntegerField()
    cards_per_pack = models.IntegerField()

    def __str__(self):
        return "%s %s" % (self.set, self.type)

    @property
    def cards_per_box(self):
        return self.cards_per_pack * self.packs_per_box

class Box(models.Model):
    product = models.ForeignKey("Product", on_delete=models.PROTECT)
    video = models.ForeignKey("Video", on_delete=models.PROTECT)
    order = models.IntegerField()

    def __str__(self):
        return "%s-%s" % (self.video, self.order)

    def pull_count(self):
        return Pull.objects.filter(box=self).count()

    def display(self):
        disp = ""
        for pull in self.pull_set.all():
            disp += "%s\n" % pull
        return disp
