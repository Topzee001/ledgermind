from django.contrib import admin
from .models import Business


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ['name', 'industry', 'owner', 'created_at']
    list_filter = ['industry', 'created_at']
    search_fields = ['name', 'owner__email']
