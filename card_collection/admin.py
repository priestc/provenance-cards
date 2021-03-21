from django.contrib import admin

from .models import (
    CollectionCard
)

class CollectionCardAdmin(admin.ModelAdmin):
    list_display = ('id', 'owner', 'self_str', 'serial')
    search_fields = ('card__subject__name', )

    def self_str(sewlf, obj):
        return str(obj)

admin.site.register(CollectionCard, CollectionCardAdmin)
