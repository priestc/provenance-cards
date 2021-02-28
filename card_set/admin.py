from django.contrib import admin

from .models import (
    Set, Manufacturer, Pull, Video, Breaker, Subset, Subject, Product, Box, Card
)

admin.site.register(Set)
admin.site.register(Manufacturer)

class PullAdmin(admin.ModelAdmin):
    list_display = ('id', 'card', 'serial', 'front_timestamp')

admin.site.register(Pull, PullAdmin)


class VideoAdmin(admin.ModelAdmin):
    list_display = ['breaker', 'youtube_identifier', 'boxes', 'pulls_recorded', 'date', 'comment']
    readonly_fields = ['display_boxes']

admin.site.register(Video, VideoAdmin)
admin.site.register(Breaker)

class SubsetAdmin(admin.ModelAdmin):
    list_display = ['set', 'name', 'color', 'serial_base', 'shorthand', 'checklist_size']

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
    list_display = ['id', 'video', 'order', 'pull_count', 'scarcity_score', 'scarcity_rank', 'how_lucky']
    inlines = [
        PullInline
    ]
    readonly_fields = ["display"]

admin.site.register(Box, BoxAdmin)
admin.site.register(Card)
