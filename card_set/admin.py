from django.contrib import admin

from .models import (
    Set, Manufacturer, Pull, Video, Breaker, Subset, Subject, Product, Box, Card
)

admin.site.register(Set)
admin.site.register(Manufacturer)

class PullAdmin(admin.ModelAdmin):
    list_display = ('id', 'card', 'serial', 'front_timestamp', 'box')
    search_fields = ('card__subject__name', )

admin.site.register(Pull, PullAdmin)


class VideoAdmin(admin.ModelAdmin):
    list_display = ['breaker', 'youtube_identifier', 'boxes', 'pulls_recorded', 'date', 'comment']
    readonly_fields = ['display_boxes']

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
admin.site.register(Subject)

admin.site.register(Product)

class PullInline(admin.TabularInline):
    model = Pull

class BoxAdmin(admin.ModelAdmin):
    list_display = ['id', 'video', 'order', 'pull_count', 'scarcity_score', 'scarcity_rank', 'how_lucky', 'missing_timestamps']
    inlines = [
        PullInline
    ]
    readonly_fields = ["display"]
    search_fields = ['video__youtube_identifier']

    def missing_timestamps(self, box):
        for pull in box.pull_set.all():
            if not pull.front_timestamp:
                return True
        return False

admin.site.register(Box, BoxAdmin)

class CardAdmin(admin.ModelAdmin):
    search_fields = ('subject__name', )
    readonly_fields = ('pull_count', )

    def pull_count(self, obj):
        return Pull.objects.filter(card=obj).count()

admin.site.register(Card, CardAdmin)
