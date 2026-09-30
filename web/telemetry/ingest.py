from datetime import datetime, timedelta, timezone

from django.db import transaction
from django.utils import timezone as django_timezone

from telemetry.models import ActivityUsage, AppUsage, Device, Report


def parse_time(value):
    if not isinstance(value, str) or not value:
        raise ValueError("Aikaleima puuttuu")
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def as_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def as_float(value, default=None):
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def non_negative(value, default=0):
    number = as_int(value, default)
    return number if number > 0 else 0


@transaction.atomic
def store_report(payload):
    if not isinstance(payload, dict):
        raise ValueError("Rungon pitää olla JSON-objekti")
    device_id = str(payload.get("deviceId") or "").strip()
    if not device_id or len(device_id) > 191:
        raise ValueError("deviceId puuttuu")
    period_start = parse_time(payload.get("periodStart"))
    period_end = parse_time(payload["periodEnd"]) if payload.get("periodEnd") else period_start + timedelta(hours=1)
    battery = payload.get("battery") or {}
    screen = payload.get("screen") or {}
    memory = payload.get("memory") or {}
    brightness = screen.get("brightness") or {}
    temperature = battery.get("temperatureC") or {}
    level_end = as_int(battery.get("levelEnd"), -1)
    cycle_count = as_int(battery.get("cycleCount"), -1) if battery.get("cycleCount") is not None else None
    if cycle_count is not None and cycle_count < 0:
        cycle_count = None
    thermal = as_int(battery.get("thermalStatusMax"), -1) if battery.get("thermalStatusMax") is not None else None
    if thermal is not None and thermal < 0:
        thermal = None

    device, _created = Device.objects.update_or_create(
        id=device_id,
        defaults={
            "label": str(payload.get("deviceLabel") or "")[:255],
            "agent_version": str(payload.get("agentVersion") or "")[:64],
            "last_seen": django_timezone.now(),
            "last_level": level_end if 0 <= level_end <= 100 else None,
        },
    )
    report, _created = Report.objects.update_or_create(
        device=device,
        period_start=period_start,
        defaults={
            "period_end": period_end,
            "timezone_offset_minutes": as_int(payload.get("timezoneOffsetMinutes")),
            "usage_access": bool(payload.get("usageAccess", True)),
            "level_start": _level(battery.get("levelStart")),
            "level_end": _level(battery.get("levelEnd")),
            "measured_mah": as_float(battery.get("measuredMah"), 0) or 0,
            "charged_mah": as_float(battery.get("chargedMah"), 0) or 0,
            "charging_ms": non_negative(battery.get("chargingMs")),
            "discharging_ms": non_negative(battery.get("dischargingMs")),
            "temp_min": as_float(temperature.get("min")),
            "temp_max": as_float(temperature.get("max")),
            "temp_avg": as_float(temperature.get("avg")),
            "health": str(battery.get("health") or "")[:32],
            "voltage_mv_avg": as_float(battery.get("voltageMvAvg")),
            "cycle_count": cycle_count,
            "thermal_status_max": thermal,
            "confidence": str(payload.get("confidence") or "")[:32],
            "screen_interactive_ms": non_negative(screen.get("interactiveMs")),
            "screen_aod_ms": non_negative(screen.get("aodMs")),
            "screen_locked_ms": non_negative(screen.get("lockedInteractiveMs")),
            "brightness_min": as_float(brightness.get("min")),
            "brightness_max": as_float(brightness.get("max")),
            "brightness_avg": as_float(brightness.get("avg")),
            "short_session_count": non_negative(screen.get("shortSessionCount")),
            "screen_sessions": _sessions(screen.get("sessions")),
            "total_mb": as_float(memory.get("totalMb")),
            "avail_mb_min": as_float(memory.get("availMbMin")),
            "avail_mb_avg": as_float(memory.get("availMbAvg")),
            "low_memory_ms": non_negative(memory.get("lowMemoryMs")),
            "gps_enabled_ms": non_negative(payload.get("gpsEnabledMs")),
            "system_mah": as_float(payload.get("systemMah"), 0) or 0,
        },
    )
    report.apps.all().delete()
    for raw in (payload.get("apps") or [])[:400]:
        if not isinstance(raw, dict):
            continue
        package_name = str(raw.get("packageName") or "").strip()
        if not package_name:
            continue
        app = AppUsage.objects.create(
            report=report,
            package_name=package_name[:255],
            foreground_ms=non_negative(raw.get("foregroundMs")),
            rx_bytes=non_negative(raw.get("rxBytes")),
            tx_bytes=non_negative(raw.get("txBytes")),
            mobile_rx_bytes=non_negative(raw.get("mobileRxBytes")),
            mobile_tx_bytes=non_negative(raw.get("mobileTxBytes")),
            wifi_rx_bytes=non_negative(raw.get("wifiRxBytes")),
            wifi_tx_bytes=non_negative(raw.get("wifiTxBytes")),
            gps_overlap_ms=non_negative(raw.get("gpsOverlapMs")),
            camera_in_use_ms=non_negative(raw.get("cameraInUseMs")),
            torch_on_ms=non_negative(raw.get("torchOnMs")),
            estimated_mah=as_float(raw.get("estimatedMah"), 0) or 0,
        )
        ActivityUsage.objects.bulk_create(
            [
                ActivityUsage(
                    app_usage=app,
                    class_name=str(activity.get("className") or "")[:512],
                    foreground_ms=non_negative(activity.get("foregroundMs")),
                    estimated_mah=as_float(activity.get("estimatedMah"), 0) or 0,
                )
                for activity in (raw.get("activities") or [])[:30]
                if isinstance(activity, dict) and activity.get("className")
            ]
        )
    cutoff = django_timezone.now() - timedelta(days=90)
    Report.objects.filter(period_start__lt=cutoff).delete()
    return report


def _level(value):
    number = as_int(value, -1)
    return number if 0 <= number <= 100 else None


def _sessions(value):
    if not isinstance(value, list):
        return []
    cleaned = []
    for item in value[:30]:
        if not isinstance(item, dict):
            continue
        cleaned.append(
            {
                "start": str(item.get("start") or ""),
                "durationMs": non_negative(item.get("durationMs")),
                "locked": bool(item.get("locked")),
                "brightnessAvg": as_float(item.get("brightnessAvg")),
                "packageName": str(item.get("packageName") or ""),
                "className": str(item.get("className") or ""),
            }
        )
    return cleaned
