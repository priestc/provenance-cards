from django.db import models

# Create your models here.

class CollectionCard(models.Model):
    card = models.ForeignKey('card_set.Card', on_delete=models.PROTECT)
    serial = models.IntegerField(default=None, null=True)
    owner = models.ForeignKey('auth.User', on_delete=models.PROTECT)
    damage = models.TextField()

    def __str__(self):
        if not self.card.subset.serial_base:
            return str(self.card)
        return "%s (%s/%s)" % (
            self.card, self.serial, self.card.get_serial_base()
        )

    @classmethod
    def total_scarcity_for_user(cls, username, set):
        collection = cls.objects.filter(owner__username=username)
        scarcity = 0
        for card in collection.select_related('card__subset'):
            scarcity += card.card.scarcity_value()
        return scarcity

    @classmethod
    def boxes_of_scarcity_for_user(cls, username, set):
        per_box = set.average_scarcity_per_box()
        return cls.total_scarcity_for_user(username, set) / per_box

    @classmethod
    def total_product_percentage(cls, username, set):
        per_box = set.average_scarcity_per_box()
        box_pop = set.box_size_estimation()
        return cls.total_scarcity_for_user(username, set) / (per_box * box_pop) * 100

    @classmethod
    def minumum_rank(cls, username, set):
        percent = cls.total_product_percentage(username, set)
        return (100 - percent) / percent


    @classmethod
    def pull_matches(cls, username, set):
        for cc in cls.objects.filter(owner__username=username, card__subset__set=set):
            if cc.card.pull_set.filter(serial=cc.serial).exists():
                print(cc)