from django.contrib import admin

from backend.apps.taxonomy.models import EducationLevel, Language, Skill

admin.site.register(EducationLevel)
admin.site.register(Language)
admin.site.register(Skill)
