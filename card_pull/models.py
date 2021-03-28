import math
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

def timestamp_to_str(float_ts):
    return str(datetime.timedelta(seconds=math.floor(float_ts)))

class Pull(models.Model):
    serial = models.TextField(blank=True)
    card = models.ForeignKey("card_set.Card", on_delete=models.PROTECT, null=True)
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
        elif self.card.subset.multi_base_numbered:
            return "%s/%s" % (self.serial, self.card.serial_base)
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

    class Meta:
        db_table = 'card_set_pull'


class Box(models.Model):
    product = models.ForeignKey("card_set.Product", on_delete=models.PROTECT)
    video = models.ForeignKey("card_set.Video", on_delete=models.PROTECT)
    order = models.IntegerField()
    scarcity_score = models.FloatField(blank=True, default=0)
    completly_indexed = models.BooleanField(default=True)
    indexed_by = models.ForeignKey("auth.user", default=None, null=True, on_delete=models.PROTECT)
    indexed_on = models.DateTimeField(default=timezone.now, null=True)

    def __str__(self):
        return "%s %s-%s" % (self.id, self.video, self.order)

    def pull_count(self):
        return Pull.objects.filter(box=self).count()

    def display(self):
        disp = ""
        for pull in self.pull_set.all():
            disp += "[%d] %s\n" % (pull.id, pull)
        return disp

    def calculate_scarcity_score(self, verbose=False):
        if verbose: print("before:", self.scarcity_score)

        score = []
        for pull in self.pull_set.select_related('card__subset').all():
            score.append(pull.card.scarcity_value)
        self.scarcity_score = sum(score)

        self.save()
        if verbose: print("after:", self.scarcity_score)
        return self.scarcity_score

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
            sb = pull.card.serial_base or pull.card.subset.serial_base or 'U'
            auto = ' auto' if pull.card.subset.autographed else ''
            if (sb != 'U') or auto:
                icon = "<span class='hit_icon%s'>/%s</span>" % (auto, sb)
                hits.append(icon)
        return " ".join(hits)

    class Meta:
        db_table = 'card_set_box'
