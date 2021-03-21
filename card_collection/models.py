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
