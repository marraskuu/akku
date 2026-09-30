import json

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from telemetry.models import AppUsage, Device, Report

PAYLOAD = {
    "deviceId": "phone-1",
    "deviceLabel": "Varasto",
    "agentVersion": "1.0.0",
    "periodStart": "2026-09-30T08:00:00Z",
    "periodEnd": "2026-09-30T09:00:00Z",
    "timezoneOffsetMinutes": 180,
    "usageAccess": True,
    "confidence": "charge_counter",
    "battery": {"levelStart": 80, "levelEnd": 70, "measuredMah": 400, "chargedMah": 0},
    "screen": {"interactiveMs": 1200000, "aodMs": 600000, "lockedInteractiveMs": 10000, "brightness": {"avg": 80}},
    "memory": {"totalMb": 8192, "availMbMin": 1500, "availMbAvg": 2100, "lowMemoryMs": 0},
    "gpsEnabledMs": 0,
    "systemMah": 40,
    "apps": [
        {
            "packageName": "com.example.camera",
            "foregroundMs": 900000,
            "rxBytes": 1000,
            "txBytes": 200,
            "cameraInUseMs": 800000,
            "torchOnMs": 40000,
            "estimatedMah": 360,
            "activities": [{"className": ".CameraActivity", "foregroundMs": 800000, "estimatedMah": 320}],
        }
    ],
}


@override_settings(INGEST_TOKEN="secret-token")
class TelemetryTests(TestCase):
    def test_rejects_missing_token(self):
        response = self.client.post("/v1/telemetry", data=json.dumps(PAYLOAD), content_type="application/json")
        self.assertEqual(response.status_code, 401)

    def test_upserts_same_hour(self):
        self._post(PAYLOAD)
        updated = json.loads(json.dumps(PAYLOAD))
        updated["battery"]["measuredMah"] = 410
        updated["battery"]["levelEnd"] = 68
        self._post(updated)
        self.assertEqual(Device.objects.count(), 1)
        self.assertEqual(Report.objects.count(), 1)
        report = Report.objects.get()
        self.assertEqual(report.measured_mah, 410)
        self.assertEqual(report.level_end, 68)
        self.assertEqual(AppUsage.objects.count(), 1)
        self.assertEqual(report.apps.get().activities.get().class_name, ".CameraActivity")

    def test_dashboard_requires_login_and_lists_phone(self):
        self._post(PAYLOAD)
        anonymous = self.client.get("/")
        self.assertEqual(anonymous.status_code, 302)
        user = User.objects.create_user("katselija", password="salaisuus-123")
        self.client.force_login(user)
        page = self.client.get("/")
        self.assertContains(page, "Varasto")
        detail = self.client.get("/devices/phone-1/")
        self.assertContains(detail, "com.example.camera")
        self.assertContains(detail, "CameraActivity")
        self.assertContains(detail, "Koko puhelimen vapaa RAM")

    def _post(self, payload):
        response = self.client.post(
            "/v1/telemetry",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer secret-token",
        )
        self.assertEqual(response.status_code, 201)
