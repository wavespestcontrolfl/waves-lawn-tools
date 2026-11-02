import io
import json
import unittest
import urllib.error
from urllib.parse import parse_qsl, urlsplit

import waves_lawn_tools as pkg
from waves_lawn_tools import api


class FakeResponse:
    def __init__(self, status, body):
        self.status = status
        self._body = body if isinstance(body, str) else json.dumps(body)

    def read(self):
        return self._body.encode("utf-8")

    def close(self):
        pass


class FakeOpener:
    """Records requests; answers with a fixed status and body (raises like urllib for 4xx/5xx when asked)."""

    def __init__(self, status, body, raise_http_error=False):
        self.status = status
        self.body = body
        self.raise_http_error = raise_http_error
        self.calls = []

    def open(self, request, timeout=None):
        self.calls.append({"url": request.full_url, "headers": {k.lower(): v for k, v in request.header_items()}, "timeout": timeout})
        if self.raise_http_error and self.status >= 400:
            text = self.body if isinstance(self.body, str) else json.dumps(self.body)
            raise urllib.error.HTTPError(request.full_url, self.status, "error", {}, io.BytesIO(text.encode("utf-8")))
        return FakeResponse(self.status, self.body)


class Client(unittest.TestCase):
    def test_get_watering_plan_sends_only_the_parameters_given_a_boolean_sensor_as_1_0(self):
        opener = FakeOpener(200, {"plan": {"action": "run"}})
        body = api.get_watering_plan(zip="34205", head="spray", minutes=20, sensor=True, grass=None, opener=opener)
        self.assertEqual(body["plan"]["action"], "run")
        url = urlsplit(opener.calls[0]["url"])
        self.assertEqual(f"{url.scheme}://{url.netloc}{url.path}", "https://portal.wavespestcontrol.com/api/public/watering-plan")
        self.assertEqual(dict(parse_qsl(url.query)), {"zip": "34205", "head": "spray", "minutes": "20", "sensor": "1"})
        self.assertEqual(opener.calls[0]["headers"]["accept"], "application/json")
        self.assertIn("waves-lawn-tools", opener.calls[0]["headers"]["user-agent"])

    def test_sensor_false_is_sent_as_0_and_empty_values_are_dropped(self):
        opener = FakeOpener(200, {})
        api.get_watering_plan(location="venice-fl", sensor=False, grass="", opener=opener)
        self.assertEqual(opener.calls[0]["url"], "https://portal.wavespestcontrol.com/api/public/watering-plan?location=venice-fl&sensor=0")

    def test_get_pest_forecast_locations_returns_the_list_itself(self):
        opener = FakeOpener(200, {"locations": [{"slug": "bradenton-fl", "label": "Bradenton, FL"}]})
        locations = api.get_pest_forecast_locations(opener=opener)
        self.assertEqual(locations[0]["slug"], "bradenton-fl")
        self.assertEqual(urlsplit(opener.calls[0]["url"]).path, "/api/public/pest-forecast/locations")

    def test_get_pest_forecast_and_get_yard_calendar_hit_their_paths_with_their_parameters(self):
        opener = FakeOpener(200, {})
        api.get_pest_forecast(location="venice-fl", opener=opener)
        api.get_yard_calendar(month=11, grass="sta", opener=opener, base_url="http://localhost:3000")
        self.assertEqual(opener.calls[0]["url"], "https://portal.wavespestcontrol.com/api/public/pest-forecast?location=venice-fl")
        self.assertEqual(opener.calls[1]["url"], "http://localhost:3000/api/public/yard-calendar?month=11&grass=sta")

    def test_get_pest_pressure_index_asks_for_json_by_default_and_csv_text_on_request(self):
        opener = FakeOpener(200, {"name": "Waves Pest Pressure Index", "min_visits": 20, "groups": []})
        body = api.get_pest_pressure_index(opener=opener)
        self.assertEqual(body["min_visits"], 20)
        self.assertEqual(opener.calls[0]["url"], "https://portal.wavespestcontrol.com/api/public/pest-pressure-index")
        self.assertEqual(opener.calls[0]["headers"]["accept"], "application/json")

        text = "county,service_line,visits,average,median,window_start,window_end\nManatee,pest,54,2.2,1.5,2026-09-24,2026-11-01\n"
        csv_opener = FakeOpener(200, text)
        self.assertEqual(api.get_pest_pressure_index(format="csv", opener=csv_opener), text)
        self.assertEqual(csv_opener.calls[0]["url"], "https://portal.wavespestcontrol.com/api/public/pest-pressure-index?format=csv")
        self.assertEqual(csv_opener.calls[0]["headers"]["accept"], "text/csv")

        with self.assertRaises(ValueError):
            api.get_pest_pressure_index(format="xml", opener=opener)

    def test_an_error_answer_raises_waves_api_error_with_the_status_and_the_api_code(self):
        payload = {"error": "unsupported_zip", "message": "That ZIP code is not in a supported Florida area."}
        for raises in (False, True):  # a returned 400 and a urllib HTTPError both end the same way
            with self.subTest(http_error=raises):
                opener = FakeOpener(400, payload, raise_http_error=raises)
                with self.assertRaises(api.WavesApiError) as caught:
                    api.get_watering_plan(zip="99999", opener=opener)
                err = caught.exception
                self.assertEqual(err.status, 400)
                self.assertEqual(err.code, "unsupported_zip")
                self.assertIn("not in a supported Florida area", str(err))

    def test_an_error_without_a_json_body_still_raises_with_the_status(self):
        with self.assertRaises(api.WavesApiError) as caught:
            api.get_yard_calendar(opener=FakeOpener(503, "<html>down</html>", raise_http_error=True))
        self.assertEqual(caught.exception.status, 503)
        self.assertIsNone(caught.exception.code)
        self.assertEqual(str(caught.exception), "Waves API answered 503")

    def test_the_error_message_falls_back_to_the_code(self):
        self.assertEqual(str(api.WavesApiError.from_body(429, {"error": "rate_limited"})), "rate_limited")

    def test_the_timeout_is_passed_to_the_opener(self):
        opener = FakeOpener(200, {})
        api.get_pest_forecast(opener=opener, timeout=3)
        self.assertEqual(opener.calls[0]["timeout"], 3)

    def test_the_package_root_exports_the_math_and_the_client_together(self):
        self.assertTrue(callable(pkg.build_week_plan))
        self.assertTrue(callable(pkg.derive_irrigation_inches_per_week))
        self.assertTrue(callable(pkg.get_watering_plan))
        self.assertTrue(callable(pkg.get_pest_pressure_index))
        self.assertEqual(pkg.BASE_URL, "https://portal.wavespestcontrol.com")
        self.assertEqual(pkg.__version__, "1.2.0")


if __name__ == "__main__":
    unittest.main()
