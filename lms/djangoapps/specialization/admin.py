from django.contrib import admin
from .models import specializations

class SpecializationAdmin(admin.ModelAdmin):
    
    list_display = [
        'name'
    ]

    search_fields = ['name']

admin.site.register(specializations)