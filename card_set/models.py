import collections
import datetime
import glob
import json
import math
import os

from django.db import models
from django.utils.text import slugify
from django.conf import settings

from moviepy.editor import VideoFileClip, concatenate_videoclips

import youtube_dl
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
        pulls = Pull.objects.filter(card__subset__set=self).count()
        boxes = Box.objects.filter(product__set=self).count()
        return math.floor(pulls / boxes)

    def best_subsets_for_estimation(self):
        if self.product_set.count() > 1:
            return
        pop = models.F('checklist_size') + models.F('serial_base')
        best_subsets = []
        for subset in self.subset_set.annotate(pop=pop).order_by('-pop'):
            if not best_subsets or best_subsets[-1].pop == subset.pop:
                best_subsets.append(subset)
        return best_subsets

    def box_size_estimation(self):
        sizes = []
        for subset in self.best_subsets_for_estimation():
            est = subset.estimate_set_size()
            sizes.append(list(est.values())[0])
        if not sizes:
            return
        return int(sum(sizes) / len(sizes))

    def estimated_box_percentage(self):
        est = self.box_size_estimation()
        if not est:
            return
        boxes = Box.objects.filter(product__set=self).count()
        return boxes / est * 100

    def all_subsets(self, categories=False):
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

        if categories:
            return {
                'Autographs': dict(autographs), "Subsets": dict(subsets)
            }
        return {**autographs, **subsets}


    def get_subset_dropdowns(self):
        subsets = self.all_subsets()
        menus = collections.defaultdict(list)

        for name, kinds in subsets.items():
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

    def get_subject_list(self):
        return list(
            Subject.objects.filter(card__subset__set=self).values_list('name', flat=True).distinct()
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

    def estimated_population(self):
        if self.serial_base:
            return
        est = self.set.estimated_box_percentage() / 100.0
        if not est:
            return
        pulled = Pull.objects.filter(card__subset=self).count()
        return int((pulled / est) / self.checklist_size)

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
        pulls = Pull.objects.filter(box__product=product, card__subset=self).order_by('card__subject')
        return {
            'matched_boxes': [p.box for p in pulls],
            'total_found': pulls
        }

    def pull_count(self):
        summary = collections.defaultdict(lambda: 0)
        for pull in Pull.objects.filter(card__subset=self).values('card__subject__name'):
            summary[pull['card__subject__name']] += 1

        return dict(summary)

    def seen_checklist_size(self):
        return Pull.objects.filter(card__subset=self).values("subject").distinct().count()

    def seen_percentage(self):
        if not self.serial_base:
            return
        return 100.0 * self.seen_checklist_size() / self.checklist_size

    def pulls_for_subject(self, subject):
        pulls = Pull.objects.filter(card__subset=self, card__subject=subject)
        return pulls

    class Meta:
        ordering = ("-serial_base", )
        unique_together = ['set', 'name', 'serial_base', 'color']

class Subject(models.Model):
    name = models.TextField()
    variation = models.TextField(blank=True)
    slug = models.SlugField()
    #rookie_year = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return "%s %s" % (self.name, self.variation)

    class Meta:
        ordering = ('name', )

    def save(self, *a, **k):
        self.slug = slugify(self.name)
        super(Subject, self).save(*a, **k)

class Video(models.Model):
    youtube_identifier = models.TextField(unique=True)
    breaker = models.ForeignKey("Breaker", on_delete=models.PROTECT)
    comment = models.TextField(blank=True)
    date = models.DateTimeField(null=True)

    @classmethod
    def get_youtube_info(cls, youtube_identifier):
        if youtube_identifier.startswith("https://www.youtube.com/watch?v="):
            youtube_identifier = youtube_identifier[32:]
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

    def last_pull_timestamp(self):
        a = Pull.objects.filter(box__video=self).aggregate(m=models.Max('front_timestamp'))
        return a['m']

    def archive(self):
        yi = self.youtube_identifier
        ap = settings.ARCHIVE_PATH
        tmpl = os.path.join(ap, '%(id)s.%(ext)s')
        g = glob.glob(os.path.join(ap, yi + ".*"))
        if g:
            print("%s already exists, skipping" % g[0])
            return
        try:
            ydl = youtube_dl.YoutubeDL({'outtmpl': tmpl})
            ydl.download(['https://www.youtube.com/watch?v=%s' % yi])
        except Exception as exc:
            print(exc.__class__.__name__, exc)

    def get_archive(self):
        yi = self.youtube_identifier
        ap = settings.ARCHIVE_PATH
        tmpl = os.path.join(ap, '%(id)s.%(ext)s')
        return glob.glob(os.path.join(ap, yi + ".*"))[0]

    def video_link(self, timestamp=None):
        yt = self.youtube_identifier
        if yt:
            ts = "?t=%d" % (timestamp or 0)
            return '<a href="https://youtu.be/%s%s">Link</a>' % (yt, ts)

class Breaker(models.Model):
    name = models.TextField()

    def __str__(self):
        return self.name

def timestamp_to_str(float_ts):
    return str(datetime.timedelta(seconds=math.floor(float_ts)))

class Pull(models.Model):
    serial = models.TextField(blank=True)
    card = models.ForeignKey("Card", on_delete=models.PROTECT, null=True)
    front_timestamp = models.FloatField(blank=True, null=True)
    back_timestamp = models.FloatField(blank=True, null=True)
    damage = models.TextField(blank=True)
    box = models.ForeignKey("Box", on_delete=models.PROTECT, null=True)

    def __str__(self):
        serial = self.show_identifier()
        #ts = "(%s to %s)" % (self.front_timestamp_str(), self.next_timestamp_str())
        return "%s %s" % (self.card, serial)

    def show_identifier(self):
        if self.card.subset.serial_base and not self.serial:
            return "?/%s" % self.card.subset.serial_base
        elif self.serial:
            return "%s/%s" % (self.serial, self.card.subset.serial_base)
        else:
            return "Unnumbered"

    def next_timestamp_str(self):
        return timestamp_to_str(self.front_timestamp + 5)
        o = self.box.pull_set.filter(front_timestamp__gt=self.front_timestamp)
        try:
            ts = o.order_by('front_timestamp')[0].front_timestamp
        except IndexError:
            # last card in box, use 5 second clip
            return timestamp_to_str(self.front_timestamp + 5)
        return timestamp_to_str(ts)

    def front_timestamp_str(self):
        return timestamp_to_str(self.front_timestamp)

    def video_link(self):
        return self.box.video.video_link(timestamp=self.front_timestamp)


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

    def best_examples(self):
        return self.box_set.order_by('-scarcity_score')[:5]

    def worst_examples(self):
        boxes = list(self.box_set.order_by('scarcity_score')[:5])
        boxes.reverse()
        return boxes

    def get_luck_ranges(self):
        all_boxes = Box.objects.filter(product=self)
        box_count = all_boxes.count()
        unlucky_base = all_boxes.order_by("scarcity_score")
        lucky_base = unlucky_base.reverse()
        return {
            'mega_lucky': lucky_base[20].scarcity_score if box_count >= 20 else 0,
            'super_lucky': lucky_base[math.floor(box_count/6.0)].scarcity_score,
            'lucky': lucky_base[math.floor(box_count/4)].scarcity_score,
            'unlucky': unlucky_base[math.floor(box_count/4)].scarcity_score,
            'super_unlucky': unlucky_base[math.floor(box_count/6.0)].scarcity_score,
            'mega_unlucky': unlucky_base[20].scarcity_score if box_count >= 20 else 0,
        }

    @classmethod
    def potential_rank(cls, product_id, scarcity_score, direction):
        boxes = Box.objects.filter(product_id=product_id).order_by("scarcity_score")
        if direction == 'top':
            tag = 'gte'
        elif direction == 'bottom':
            tag = 'lte'
        return boxes.filter(**{"scarcity_score__%s" % tag: scarcity_score}).count() + 1

    def breaker_rundown(self):
        breakers = collections.defaultdict(dict)
        for box in Box.objects.filter(product=self).select_related('video', 'video__breaker').all():
            data = breakers[box.video.breaker]
            scarcity = data.get('scarcity', 0)
            data['scarcity'] = scarcity + box.scarcity_score
            count = data.get('count', 0)
            data['count'] = count + 1

        for breaker, data in breakers.items():
            data['avg'] = data['scarcity'] / data['count']

        return sorted(
            [[breaker, data['count'], data['avg']] for breaker, data in breakers.items()],
            key=lambda x: x[2], reverse=True
        )


class Box(models.Model):
    product = models.ForeignKey("Product", on_delete=models.PROTECT)
    video = models.ForeignKey("Video", on_delete=models.PROTECT)
    order = models.IntegerField()
    scarcity_score = models.FloatField(blank=True, default=0)

    def __str__(self):
        return "%s-%s" % (self.video, self.order)

    def pull_count(self):
        return Pull.objects.filter(box=self).count()

    def display(self):
        disp = ""
        for pull in self.pull_set.all():
            disp += "%s\n" % pull
        return disp

    def calculate_scarcity_score(self):
        score = 0
        for pull in self.pull_set.select_related('card__subset').all():
            sb = pull.card.subset.serial_base
            score += 0 if not sb else 1.0 / sb
        self.scarcity_score = score
        self.save()
        return score

    def scarcity_rank(self):
        return Box.objects.filter(scarcity_score__gte=self.scarcity_score).count()

    def how_lucky(self):
        ranges = self.product.get_luck_ranges()
        if self.scarcity_score > ranges['mega_lucky']:
            return "Top 20 All Time"
        if self.scarcity_score < ranges['mega_unlucky']:
            return "Bottom 20 All Time"
        if self.scarcity_score > ranges['super_lucky']:
            return "super lucky"
        if self.scarcity_score < ranges['super_unlucky']:
            return "super unlucky"
        if self.scarcity_score > ranges['lucky']:
            return "lucky"
        if self.scarcity_score < ranges['unlucky']:
            return "unlucky"
        return "normal"

    def video_link(self):
        first_ts = self.pull_set.order_by("front_timestamp")[0].front_timestamp
        return self.video.video_link(timestamp=first_ts)

    def hits(self):
        hits = []
        for pull in self.pull_set.select_related("card__subset").order_by('card__subset__serial_base'):
            sb = pull.card.subset.serial_base
            if sb:
                icon = "<span class='hit_icon'>/%s</span>" % sb
                hits.append(icon)
        return " ".join(hits)

class Card(models.Model):
    subject = models.ForeignKey('Subject', on_delete=models.PROTECT)
    subset = models.ForeignKey('Subset', on_delete=models.PROTECT)
    card_number = models.CharField(max_length=12, blank=True)

    def front_video(self):
        clips = []
        for pull in self.pull_set.all():
            if not pull.front_timestamp:
                continue
            p = pull.box.video.get_archive()
            if  p.endswith("mkv"):
                continue
            ts = pull.front_timestamp
            print(VideoFileClip(p).size)
            v = VideoFileClip(p).subclip(ts, ts+5)
            clips.append(v)

        final = concatenate_videoclips(clips, method="compose")
        final.write_videofile("composite.mp4")

    def __str__(self):
        return "%s %s" % (self.subset, self.subject)

    class Mega:
        ordering = ('subject__name', 'subset__name')
