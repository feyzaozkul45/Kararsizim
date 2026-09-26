from django.contrib import admin

from .models import Option, Poll, Vote


class OptionInline(admin.TabularInline):
    model = Option
    extra = 0


@admin.register(Poll)
class PollAdmin(admin.ModelAdmin):
    list_display = ("question", "author", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("question", "author__username")
    inlines = [OptionInline]


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ("poll", "option", "user", "created_at")
    readonly_fields = ("created_at",)
