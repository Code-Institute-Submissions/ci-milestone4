from django.contrib import admin
from .models import UserProfile


class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'user_tel',
        'user_street_address1',
        'user_postcode',
    )


admin.site.register(UserProfile, UserProfileAdmin)
