from django.contrib import admin

from telemetry.models import ActivityUsage, AppUsage, Device, Report


class AppUsageInline(admin.TabularInline):
    model = AppUsage
    extra = 0


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("id", "label", "last_level", "last_seen", "agent_version")
    search_fields = ("id", "label")


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("device", "period_start", "level_end", "measured_mah", "screen_interactive_ms")
    list_filter = ("confidence",)
    inlines = [AppUsageInline]


admin.site.register(ActivityUsage)
