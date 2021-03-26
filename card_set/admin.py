from django.contrib import admin

from .models import (
    Set, Manufacturer, Video, Breaker, Subset, Subject, Product, Card
)
from card_collection.models import CollectionCard
from card_pull.models import Pull

admin.site.register(Set)
admin.site.register(Manufacturer)

class VideoAdmin(admin.ModelAdmin):
    list_display = ['breaker', 'youtube_identifier', 'boxes', 'pulls_recorded', 'date', 'comment']
    readonly_fields = ['display_boxes']
    search_fields = ('youtube_identifier', 'breaker__name')

admin.site.register(Video, VideoAdmin)
admin.site.register(Breaker)

class SubsetAdmin(admin.ModelAdmin):
    list_display = ['set', 'name', 'color', 'autographed', 'serial_base', 'shorthand', 'checklist_size']
    readonly_fields = ['cards']

    def cards(self, obj):
        return "\n".join(str(x) for x in obj.card_set.all())

    def estimated_set_size(self, obj):
        disp = ""
        estimation_data = obj.estimate_set_size()
        if not estimation_data:
            return

        for prod, estimate in estimation_data.items():
            if estimate:
                disp += "%s: %.d" % (prod.type, estimate)
            else:
                disp += "%s: N/A" % (prod.type)
        return disp

admin.site.register(Subset, SubsetAdmin)

class SubjectAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    readonly_fields = ['show_cards']

    def show_cards(self, obj):
        return '\n'.join(
            "[%s] %s" % (x.id, str(x)) for x in Card.objects.filter(subject=obj)
        )

admin.site.register(Subject, SubjectAdmin)
admin.site.register(Product)

class CardAdmin(admin.ModelAdmin):
    search_fields = ('subject__name', 'id', 'subset__name')
    readonly_fields = ('pull_count', 'collection_count')

    def pull_count(self, obj):
        return Pull.objects.filter(card=obj).count()

    def collection_count(self, obj):
        return CollectionCard.objects.filter(card=obj).count()

admin.site.register(Card, CardAdmin)
