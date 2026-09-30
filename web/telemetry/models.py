from django.db import models


class Device(models.Model):
    id = models.CharField(primary_key=True, max_length=191)
    label = models.CharField(max_length=255, blank=True)
    agent_version = models.CharField(max_length=64, blank=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    last_level = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["label", "id"]

    def __str__(self):
        return self.label or self.id

    @property
    def display_name(self):
        return self.label or self.id


class Report(models.Model):
    device = models.ForeignKey(Device, related_name="reports", on_delete=models.CASCADE)
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    timezone_offset_minutes = models.SmallIntegerField(default=0)
    usage_access = models.BooleanField(default=True)
    level_start = models.PositiveSmallIntegerField(null=True, blank=True)
    level_end = models.PositiveSmallIntegerField(null=True, blank=True)
    measured_mah = models.FloatField(default=0)
    charged_mah = models.FloatField(default=0)
    charging_ms = models.BigIntegerField(default=0)
    discharging_ms = models.BigIntegerField(default=0)
    temp_min = models.FloatField(null=True, blank=True)
    temp_max = models.FloatField(null=True, blank=True)
    temp_avg = models.FloatField(null=True, blank=True)
    health = models.CharField(max_length=32, blank=True)
    voltage_mv_avg = models.FloatField(null=True, blank=True)
    cycle_count = models.IntegerField(null=True, blank=True)
    thermal_status_max = models.PositiveSmallIntegerField(null=True, blank=True)
    confidence = models.CharField(max_length=32, blank=True)
    screen_interactive_ms = models.BigIntegerField(default=0)
    screen_aod_ms = models.BigIntegerField(default=0)
    screen_locked_ms = models.BigIntegerField(default=0)
    brightness_min = models.FloatField(null=True, blank=True)
    brightness_max = models.FloatField(null=True, blank=True)
    brightness_avg = models.FloatField(null=True, blank=True)
    short_session_count = models.PositiveIntegerField(default=0)
    screen_sessions = models.JSONField(default=list, blank=True)
    total_mb = models.FloatField(null=True, blank=True)
    avail_mb_min = models.FloatField(null=True, blank=True)
    avail_mb_avg = models.FloatField(null=True, blank=True)
    low_memory_ms = models.BigIntegerField(default=0)
    gps_enabled_ms = models.BigIntegerField(default=0)
    system_mah = models.FloatField(default=0)
    received_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["device", "period_start"], name="uniq_device_period"),
        ]
        ordering = ["period_start"]

    def __str__(self):
        return f"{self.device_id} {self.period_start:%Y-%m-%d %H:%M}"


class AppUsage(models.Model):
    report = models.ForeignKey(Report, related_name="apps", on_delete=models.CASCADE)
    package_name = models.CharField(max_length=255)
    foreground_ms = models.BigIntegerField(default=0)
    rx_bytes = models.BigIntegerField(default=0)
    tx_bytes = models.BigIntegerField(default=0)
    mobile_rx_bytes = models.BigIntegerField(default=0)
    mobile_tx_bytes = models.BigIntegerField(default=0)
    wifi_rx_bytes = models.BigIntegerField(default=0)
    wifi_tx_bytes = models.BigIntegerField(default=0)
    gps_overlap_ms = models.BigIntegerField(default=0)
    camera_in_use_ms = models.BigIntegerField(default=0)
    torch_on_ms = models.BigIntegerField(default=0)
    estimated_mah = models.FloatField(default=0)

    class Meta:
        ordering = ["-estimated_mah", "package_name"]


class ActivityUsage(models.Model):
    app_usage = models.ForeignKey(AppUsage, related_name="activities", on_delete=models.CASCADE)
    class_name = models.CharField(max_length=512)
    foreground_ms = models.BigIntegerField(default=0)
    estimated_mah = models.FloatField(default=0)

    class Meta:
        ordering = ["-estimated_mah", "class_name"]
