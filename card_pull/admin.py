from django.contrib import admin

from .models import Box, Pull

class PullAdmin(admin.ModelAdmin):
    list_display = ('id', 'card', 'serial', 'front_timestamp', 'box')
    search_fields = ('card__subject__name', 'id__exact')

admin.site.register(Pull, PullAdmin)

class PullInline(admin.TabularInline):
    model = Pull

class BoxAdmin(admin.ModelAdmin):
    list_display = ['id', 'video', 'order', 'pull_count', 'scarcity_score', 'scarcity_rank', 'how_lucky', 'missing_timestamps']
    #inlines = [PullInline]
    readonly_fields = ["pulls"]
    search_fields = ['video__youtube_identifier', 'video__breaker__name']

    def pulls(self, obj):
        return obj.display()

    def missing_timestamps(self, box):
        for pull in box.pull_set.all():
            if not pull.front_timestamp:
                return True
        return False

admin.site.register(Box, BoxAdmin)
