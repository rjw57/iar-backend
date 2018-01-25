from django.contrib import admin
from assets.models import Asset


class AssetAdmin(admin.ModelAdmin):
    fields = ('name', 'department', 'owner')


admin.site.register(Asset, AssetAdmin)
