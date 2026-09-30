import hmac
import json
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from telemetry.ingest import store_report
from telemetry.models import AppUsage, Device, Report


def health(_request):
    return JsonResponse({"ok": True})


@csrf_exempt
def ingest(request):
    if request.method != "POST":
        return HttpResponse(status=405)
    expected = settings.INGEST_TOKEN
    header = request.headers.get("Authorization", "")
    token = header[7:].strip() if header.startswith("Bearer ") else ""
    if not expected or len(token) != len(expected) or not hmac.compare_digest(token, expected):
        return HttpResponse(status=401)
    try:
        payload = json.loads(request.body.decode("utf-8"))
        store_report(payload)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        return HttpResponse(status=400)
    return HttpResponse(status=201)


@login_required
def device_list(request):
    now = timezone.now()
    today = timezone.localtime(now).replace(hour=0, minute=0, second=0, microsecond=0)
    devices = list(Device.objects.all().order_by("-last_seen"))
    grouped = {}
    for report in Report.objects.filter(period_start__gte=today):
        bucket = grouped.setdefault(report.device_id, {"screen": 0, "mah": 0.0, "memory": None})
        bucket["screen"] += report.screen_interactive_ms
        bucket["mah"] += report.measured_mah
        if report.avail_mb_min is not None:
            bucket["memory"] = report.avail_mb_min if bucket["memory"] is None else min(bucket["memory"], report.avail_mb_min)
    stale_before = now - timedelta(hours=2)
    rows = []
    for device in devices:
        stats = grouped.get(device.id, {"screen": 0, "mah": 0.0, "memory": None})
        rows.append(
            {
                "device": device,
                "stale": device.last_seen is None or device.last_seen < stale_before,
                "screen": stats["screen"],
                "mah": stats["mah"],
                "memory": stats["memory"],
            }
        )
    return render(request, "telemetry/device_list.html", {"rows": rows})


@login_required
def device_detail(request, device_id):
    device = get_object_or_404(Device, pk=device_id)
    span = "7d" if request.GET.get("range") == "7d" else "24h"
    start = timezone.now() - (timedelta(days=7) if span == "7d" else timedelta(hours=24))
    reports = list(device.reports.filter(period_end__gte=start).order_by("period_start"))
    levels = [report.level_end for report in reports if report.level_end is not None]
    memory = [report.avail_mb_avg for report in reports if report.avail_mb_avg is not None]
    screen = {
        "interactive": sum(report.screen_interactive_ms for report in reports),
        "aod": sum(report.screen_aod_ms for report in reports),
        "locked": sum(report.screen_locked_ms for report in reports),
        "brightness": _weighted_brightness(reports),
        "low_memory": sum(report.low_memory_ms for report in reports),
        "system": sum(report.system_mah for report in reports),
        "measured": sum(report.measured_mah for report in reports),
    }
    apps = _apps(device, start)
    max_mah = max((app["mah"] for app in apps), default=0) or 1
    missing_usage = any(not report.usage_access for report in reports[-3:])
    return render(
        request,
        "telemetry/device_detail.html",
        {
            "device": device,
            "span": span,
            "screen": screen,
            "apps": apps,
            "max_mah": max_mah,
            "level_chart": _chart(levels),
            "memory_chart": _chart(memory),
            "missing_usage": missing_usage,
            "confidence": reports[-1].confidence if reports else "",
        },
    )


def _weighted_brightness(reports):
    total = 0
    weighted = 0.0
    for report in reports:
        if report.brightness_avg is None or report.screen_interactive_ms <= 0:
            continue
        total += report.screen_interactive_ms
        weighted += report.brightness_avg * report.screen_interactive_ms
    return weighted / total if total else None


def _apps(device, start):
    buckets = {}
    usages = (
        AppUsage.objects.filter(report__device=device, report__period_end__gte=start)
        .prefetch_related("activities")
    )
    for usage in usages:
        bucket = buckets.setdefault(
            usage.package_name,
            {
                "package": usage.package_name,
                "mah": 0.0,
                "foreground": 0,
                "camera": 0,
                "torch": 0,
                "rx": 0,
                "tx": 0,
                "activities": {},
            },
        )
        bucket["mah"] += usage.estimated_mah
        bucket["foreground"] += usage.foreground_ms
        bucket["camera"] += usage.camera_in_use_ms
        bucket["torch"] += usage.torch_on_ms
        bucket["rx"] += usage.rx_bytes
        bucket["tx"] += usage.tx_bytes
        for activity in usage.activities.all():
            row = bucket["activities"].setdefault(activity.class_name, {"class_name": activity.class_name, "foreground": 0, "mah": 0.0})
            row["foreground"] += activity.foreground_ms
            row["mah"] += activity.estimated_mah
    apps = []
    for bucket in buckets.values():
        activities = sorted(bucket["activities"].values(), key=lambda item: item["mah"], reverse=True)
        bucket["top_activity"] = activities[0]["class_name"] if activities else ""
        bucket["activities"] = activities
        apps.append(bucket)
    apps.sort(key=lambda item: item["mah"], reverse=True)
    return apps


def _chart(values):
    if not values:
        return None
    points = values if len(values) > 1 else [values[0], values[0]]
    low = min(points)
    high = max(points)
    span = high - low or 1
    width = 640
    height = 140
    coords = []
    for index, value in enumerate(points):
        x = index * (width / (len(points) - 1))
        y = 12 + (height - 24) * (1 - (value - low) / span)
        coords.append(f"{x:.1f},{y:.1f}")
    return {"points": " ".join(coords), "low": low, "high": high}
