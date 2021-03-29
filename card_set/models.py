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

from card_pull.models import Box, Pull

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

        for subset in self.subset_set.all():
            color = subset.color
            serial_base = subset.serial_base
            name = subset.name

            section = subsets
            if subset.autographed:
                section = autographs

            if subset.checklist_size and serial_base:
                population = -1 * int(subset.checklist_size) * int(serial_base)
            else:
                population = 0

            info = {
                "color": color, "serial_base": serial_base, 'id': subset.id,
                "pop": population
            }

            if subset.multi_base_numbered:
                info['multi_base_numbered'] = True

            section[name].append(info)

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
                payload = [
                    verbose_color(data['serial_base'], data['color']), sort
                ]
                menus['color'].append(payload)
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

    @property
    def total_scarcity(self):
        total_scarcity = Box.objects.filter(product__set=self).aggregate(s=models.Sum('scarcity_score'))['s']
        return total_scarcity

    def average_scarcity_per_box(self):
        return self.total_scarcity / Box.objects.filter(product__set=self).count()

    def calculate_cached_statistics(self, verbose=False):
        for subset in self.subset_set.all():
            subset.calculate_statistical_serial_base(verbose=verbose)
            if subset.multi_base:
                for card in subset.card_set.all():
                    card.calculate_multi_base_population(verbose=verbose)

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
    multi_base = models.BooleanField(default=False)
    multi_base_numbered = models.BooleanField(default=False)
    autographed = models.BooleanField(default=False)
    comc_color = models.TextField(default='', blank=True)
    comc_color_blank = models.BooleanField(default=False, blank=True)
    comc_name = models.TextField(default='', blank=True)
    comc_name_blank = models.BooleanField(default=False, blank=True)
    card_number_critical = models.BooleanField(default=False)
    statistical_serial_base = models.FloatField(default=0, blank=True)

    def __str__(self):
        return "%s %s (%s)" % (self.set, self.name, self.verbose_color())

    def verbose_color(self):
        return verbose_color(self.serial_base, self.color)

    def total_population(self):
        if self.multi_base_numbered:
            return sum((c.serial_base or 0) for c in self.card_set.all())

        checklist_size = self.checklist_size or self.estimate_checklist_size()
        serial_base = self.serial_base or self.statistical_serial_base

        return (
            checklist_size * serial_base
            if checklist_size and serial_base
            else None
        )

    def estimated_population(self):
        ebp = self.set.estimated_box_percentage() / 100.0
        if not ebp:
            return
        pulled = self.get_pulls().count()
        return int((pulled / ebp))

    def calculate_statistical_serial_base(self, verbose=False):
        """
        Used when serial_base is unknown. Use statistics to estimate what it
        would be.
        """
        if self.serial_base:
            return #No need to estimate when serial_base is already known
        self.statistical_serial_base = (
            self.estimated_population() / (self.checklist_size or self.estimate_checklist_size())
        )
        if verbose: print(self, "statistical serial base:", self.statistical_serial_base)
        self.save()

    def get_statistical_serial_base(self):
        return self.statistical_serial_base

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
            raise Exception("Don't use non serial numbered subsets to estimate size of total product")

        total_pop = self.total_population()
        if not total_pop:
            raise Exception("total_pop is unknown")

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
        pulls = self.get_pulls().filter(box__product=product).order_by('card__subject')
        return {
            'matched_boxes': [p.box for p in pulls],
            'total_found': pulls
        }

    def get_pulls(self):
        return Pull.objects.filter(card__subset=self)

    def pull_count(self):
        summary = collections.defaultdict(lambda: 0)

        for card in self.card_set.all():
            summary[card.subject.name] = 0

        for pull in self.get_pulls().values('card__subject__name'):
            summary[pull['card__subject__name']] += 1

        if self.multi_base:
            total_pop = sum(summary.values())
            est_ss_pop = self.estimated_population()
            summary_with_percentages = {}
            expected_percentage = 100.0 / len(summary)

            for item, count in summary.items():
                percentage = 100.0 * count / total_pop
                scarcity_factor = expected_percentage / percentage
                disp_scarcity_factor = scarcity_factor if scarcity_factor > 1 else (-1 / scarcity_factor)
                summary_with_percentages[item] = {
                    'count': count,
                    'percentage': percentage,
                    'expected_percentage': expected_percentage,
                    'scarcity_factor': disp_scarcity_factor,
                    'estimated_population': int(est_ss_pop * percentage / 100.0)
                }
            return summary_with_percentages

        return dict(summary)

    def multibase_numbered_pull_count(self):
        summary = {}

        for pull in self.get_pulls().values('card__subject__name', 'card__serial_base'):
            serial_base = pull['card__serial_base']
            name = pull['card__subject__name']
            key = "%s /%s" % (name, serial_base)
            count = summary.get(key, {'count': 0})['count']
            summary[key] = {'name': name, 'count': count + 1, 'serial_base': serial_base}

        return summary

    def seen_checklist_size(self):
        return self.get_pulls().values("subject").distinct().count()

    def seen_percentage(self):
        """
        What percentage of each card has been seen before with respect to the entire
        subset.
        """
        if not self.serial_base:
            return
        return 100.0 * self.seen_checklist_size() / (self.checklist_size or self.estimate_checklist_size())

    def pulls_for_subject(self, subject):
        return self.get_pulls().filter(card__subject=subject)

    def estimate_checklist_size(self):
        cards = Card.objects.filter(subset=self)
        if self.card_number_critical:
            return cards.exclude(card_number='').values('card_number').distinct().count()
        return cards.values('subject__id').distinct().count()

    def get_comc_link(self):
        if self.comc_color_blank:
            color = ''
        else:
            raw_color = self.comc_color or self.color
            color = "_-_%s" % raw_color.title() if raw_color else ""

        subset = self.name
        if self.comc_name:
            subset = self.comc_name

        return "https://www.comc.com/Cards/Baseball/{year}/{manufacturer}_{set}_-_{subset}{color},sh,i100".format(
            manufacturer=self.set.manufacturer, set=self.set.name.replace(" ", "_"),
            subset=subset.replace(" ", "_"), color=color, year=self.set.year
        )

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

    def comc_link(self):
        n = self.name.replace(" ", "_")
        return "https://www.comc.com/Players/Baseball/%s/sl,i100" % n

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

    @classmethod
    def full_archive(cls):
        [x.archive() for x in cls.objects.all()]


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
            disp += "Box %s (%s) \n%s\n\n" % (b.id, b.order, b.display())
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

    def boxes_by_product(self, product):
        from card_pull.models import Box
        return Box.objects.filter(video__breaker=self, product=product)

    def calc_stats_for_product(self, product):
        sum = 0
        count = 0
        self.product_boxes = list(self.boxes_by_product(product).order_by('-scarcity_score'))
        for box in self.product_boxes:
            count += 1
            sum += box.scarcity_score

        self.product_avg_scarcity = sum / count
        self.product_total_boxes = count
        return self


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

    def pull_count(self):
        return Pull.objects.filter(box__product=self).count()

    def type_plural(self):
        if self.type.endswith("x"):
            return "%ses" % self.type

    def best_examples(self):
        return self.box_set.order_by('-scarcity_score')[:5]

    def worst_examples(self):
        return self.box_set.order_by('scarcity_score')[:5]

    def median_examples(self):
        total_size = self.box_set.count()
        median = int(total_size / 2.0)
        all_boxes = self.box_set.order_by('scarcity_score')
        median_boxes = []
        for i in range(-2, 3):
            the_rank = median + i
            median_boxes.append([the_rank, all_boxes[the_rank]])

        return median_boxes

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

    def top_breakers(self, limit=20):
        breakers = Breaker.objects.filter(
            video__box__product=self
        ).annotate(count=models.Count('video__box')).order_by('-count')[:limit]
        return sorted([b.calc_stats_for_product(self) for b in breakers],
            key=lambda b: b.product_avg_scarcity, reverse=True
        )


def clean_color(color):
    if "Unnumbered" in color:
        serial_base = None
        pre_serial = color[:-10]
    elif "/" in color:
        pre_serial, serial_base = color.split("/")
        serial_base = int(serial_base)

    cleaned_color = pre_serial.strip()
    return cleaned_color, serial_base

class Card(models.Model):
    subject = models.ForeignKey('Subject', on_delete=models.PROTECT)
    subset = models.ForeignKey('Subset', on_delete=models.PROTECT)
    card_number = models.CharField(max_length=12, blank=True)
    serial_base = models.IntegerField(blank=True, null=True) # only for subsets with multi_base_numbered==True
    multi_base_population = models.FloatField(default=0, blank=True)

    @classmethod
    def get_card(cls, subset_id, card_form_line, set):
        subject, c = Subject.objects.get_or_create(name=card_form_line['subject'])
        card_opts = {}

        if not subset_id:
            # never before seen color and serial base combination, make new subset.
            cleaned_color, serial_base = clean_color(card_form_line['color'])
            subset = Subset.objects.create(
                set=set, serial_base=serial_base, name=card_form_line['subset_name'],
                color=cleaned_color
            )
        else:
            if type(subset_id) is tuple:
                subset_id, serial_base = subset_id
                card_opts = {'serial_base': serial_base}

            subset = Subset.objects.get(id=subset_id)

        if 'card_number' in card_form_line:
            card_opts['card_number'] = card_form_line['card_number']

        try:
            card, c = cls.objects.get_or_create(subset=subset, subject=subject, **card_opts)
        except cls.MultipleObjectsReturned:
            # if there's 2 versions of this card in the database, one that has
            # no card number, and one with. Use the one with.
            card = cls.objects.filter(subset=subset, subject=subject, **card_opts).exclude(card_number='').get()

        return card

    def get_pulls(self):
        return self.subset.get_pulls().filter(card__subject=self.subject)

    @property
    def statistical_serial_base(self):
        if self.subset.multi_base:
            # unnumbered cards where each card was in different quantities
            return self.multi_base_population
        if not self.subset.serial_base:
            # unnumbered cards with all the same expected pop
            return self.subset.statistical_serial_base

        # each card in the subset has the same serial_base
        return self.serial_base or self.subset.serial_base

    @property
    def scarcity_value(self):
        return (2 if self.subset.autographed else 1) / self.statistical_serial_base

    def calculate_multi_base_population(self, verbose=False):
        self.multi_base_population = (
            self.subset.estimated_population() * self.actual_subset_percentage / 100.0
        )
        if verbose:
            print(self, "statistical serial base:", self.multi_base_population)
        self.save()

    @property
    def scarcity_factor(self):
        scarcity_factor = self.expected_subset_percentage / self.actual_subset_percentage
        polarity_scarcity_factor = scarcity_factor if scarcity_factor > 1 else (-1 / scarcity_factor)
        return polarity_scarcity_factor * 100

    @property
    def expected_subset_percentage(self):
        return 100.0 / (self.subset.checklist_size or self.subset.estimate_checklist_size())

    @property
    def actual_subset_percentage(self):
        return self.get_pulls().count() / self.subset.get_pulls().count() * 100

    def front_video(self):
        return self.make_video("front")

    def back_video(self):
        return self.make_video("back")

    def make_video(self, side):
        clips = []
        for pull in self.pull_set.all():
            ts = getattr(pull, "%s_timestamp" % side)
            if not ts:
                continue
            arch = pull.box.video.get_archive()
            v = VideoFileClip(arch).subclip(ts, ts+5)
            clips.append(v)

        final = concatenate_videoclips(clips, method="compose")
        final.write_videofile("%s-%s.mp4" % (self.id, side))

    def __str__(self):
        if self.subset.multi_base_numbered:
            subset = "%s %s %s /%s" % (
                self.subset.set, self.subset.name, self.subset.color,
                self.serial_base
            )
        else:
            subset = self.subset

        card_number = " #%s " % self.card_number if self.card_number else ' '
        return "%s %s%s" % (subset, self.subject, card_number)

    def get_serial_base(self):
        if self.subset.multi_base:
            return self.serial_base
        return self.subset.serial_base

    class Meta:
        ordering = ('subject__name', 'subset__name')


def make_multibase(base_subset, all_subsets):
    base_subset.multi_base_numbered = True
    base_subset.save()

    for card in Card.objects.filter(subset__in=all_subsets):
        card.serial_base = card.subset.serial_base
        card.subset = base_subset
        card.save()
        print(card)
