import io
import unittest
import urllib.error

from waves_lawn_tools import api, explore

# Small answers shaped like the real API's, with made-up numbers.
PLAN = {
    "location": {"slug": "bradenton-fl", "label": "Bradenton, FL", "county": "Manatee"},
    "rain": {"last7Inches": 0.54, "source": "mrms"},
    "forecast": {"rainInches": 0.13, "et0Inches": 0.95},
    "need": {"targetInches": 0.75, "basis": "evapotranspiration", "netInches": 0.75},
    "plan": {"action": "run", "events": 1, "depthInches": 0.75, "minutesPerEvent": 45, "conditionalOnForecast": False, "legalMaxEvents": 1},
    "restriction": {"label": "One day a week", "maxDaysPerWeek": 1},
    "text": {"headline": "This week: about 45 minutes per turf zone", "action": "Water on your day.", "notes": ["Note one.", "Note two."]},
}

FORECAST = {
    "month_name": "November",
    "summary": "Pressure is on the lower side.",
    "weather": {"available": True, "summary": "82F, 26% chance of rain"},
    "disclaimer": "A seasonal model.",
    "pests": [
        {"key": "ants", "label": "Ants", "score": 4, "score10": 4, "baseline_comparison": "near", "level": "moderate", "trend": "flat", "note": "Cooler weather slows ants."},
        {"key": "german_roach", "label": "German Cockroaches", "score": 5, "score10": 5, "baseline_comparison": "above", "level": "moderate", "trend": "flat"},
        {"key": "mosquitoes", "label": "Mosquitoes", "score": 4, "score10": 4, "baseline_comparison": "below", "level": "low", "trend": "rising"},
    ],
}

CALENDAR = {
    "month": 11,
    "grass": "sta",
    "planAhead": ["Winter weeds are still in the pre-emergent window."],
    "items": [
        {"id": "chinch-bug", "category": "lawn", "name": "Chinch bugs", "hosts": "St. Augustine", "level": 1, "levelLabel": "Low year-round",
         "levels": [1, 1, 1, 1, 3, 3, 3, 3, 3, 1, 1, 1], "trend": None, "sign": "Yellow patches.", "infoOnly": False, "link": "/pest-identifier/chinch-bug/"},
        {"id": "sod-webworm", "category": "lawn", "name": "Tropical sod webworm", "hosts": "St. Augustine", "level": 3, "levelLabel": "Peak season",
         "levels": [1] * 8 + [3, 3, 3, 1], "trend": "easing_next_month", "sign": "Chewed blades.", "infoOnly": False, "link": "/pest-identifier/sod-webworm/"},
        {"id": "winter-weeds", "category": "weed", "name": "Winter weeds", "hosts": "Thin lawns", "level": 2, "levelLabel": "In season",
         "levels": [3, 3, 3, 2, 0, 0, 0, 0, 0, 2, 2, 3], "trend": "starts_next_month", "sign": "Rosettes.", "infoOnly": False, "link": None},
        {"id": "fact", "category": "shrub", "name": "Info item", "level": 0, "levelLabel": "Off season", "levels": [], "infoOnly": True},
    ],
}

INDEX = {
    "window": {"start": "2026-09-24", "end": "2026-11-01", "days": 39},
    "scale": {"labels": {"0": "None", "1": "Very Low", "2": "Low", "3": "Moderate", "4": "Elevated", "5": "High"}},
    "min_visits": 20,
    "groups": [
        {"county": "Sarasota", "service_line": "pest", "visits": 30, "average": 3.5, "median": 3},
        {"county": "Manatee", "service_line": "pest", "visits": 54, "average": 2.2, "median": 1.5},
    ],
    "hidden_groups": 1,
    "license": {"name": "CC BY 4.0"},
}


class Choices(unittest.TestCase):
    def test_months_and_grass(self):
        self.assertEqual(explore.month_name(11), "November")
        for bad in (0, 13, "11", True):
            with self.assertRaises(ValueError):
                explore.month_name(bad)
        self.assertEqual(explore.calendar_grass_code("st_augustine"), "sta")
        self.assertEqual(explore.calendar_grass_code("sta"), "sta")
        self.assertEqual(explore.calendar_grass_code("nonsense"), "all")
        self.assertEqual(explore.watering_grass_value("zoy"), "zoysia")
        self.assertEqual(explore.watering_grass_value("nonsense"), "unknown")
        self.assertEqual(explore.grass_label("bahia"), "Bahia")
        self.assertEqual(explore.grass_label("bah"), "Bahia")

    def test_location_choices_keep_the_api_order(self):
        locations = [{"slug": "venice-fl", "label": "Venice, FL"}, {"slug": "tampa-fl"}, {"label": "no slug"}]
        self.assertEqual(explore.location_choices(locations), [("venice-fl", "Venice, FL"), ("tampa-fl", "tampa-fl")])


class WateringPlan(unittest.TestCase):
    def test_facts_for_a_run_plan(self):
        facts = dict(explore.watering_plan_facts(PLAN))
        self.assertEqual(facts["Decision"], "Water")
        self.assertEqual(facts["Water per run"], '0.75"')
        self.assertEqual(facts["Minutes per zone"], "45")
        self.assertEqual(facts["Rain, last 7 days"], '0.54"')
        self.assertEqual(facts["Local watering limit"], "One day a week")

    def test_facts_survive_a_thin_answer(self):
        self.assertEqual(explore.watering_plan_facts({}), [])
        facts = dict(explore.watering_plan_facts({"plan": {"action": "need_only"}, "forecast": None}))
        self.assertIn("Need only", facts["Decision"])
        self.assertEqual(explore.watering_plan_text({}), {"headline": "", "action": "", "notes": []})

    def test_text(self):
        text = explore.watering_plan_text(PLAN)
        self.assertEqual(text["notes"], ["Note one.", "Note two."])


class PestForecast(unittest.TestCase):
    def test_rows_are_sorted_by_score_then_name(self):
        rows = explore.pest_forecast_rows(FORECAST)
        self.assertEqual([r["Pest"] for r in rows], ["German Cockroaches", "Ants", "Mosquitoes"])
        self.assertEqual(rows[0]["Versus normal"], "Above normal")
        self.assertEqual(rows[0]["Level"], "Moderate")
        self.assertEqual(rows[2]["Trend"], "Rising")

    def test_summary_hides_unavailable_weather(self):
        self.assertEqual(explore.pest_forecast_summary(FORECAST)["weather"], "82F, 26% chance of rain")
        off = dict(FORECAST, weather={"available": False, "summary": "stale"})
        self.assertEqual(explore.pest_forecast_summary(off)["weather"], "")
        self.assertEqual(explore.pest_forecast_rows({}), [])


class YardCalendar(unittest.TestCase):
    def test_rows_most_active_first_with_absolute_links(self):
        rows = explore.yard_calendar_rows(CALENDAR)
        self.assertEqual([r["Name"] for r in rows], ["Tropical sod webworm", "Winter weeds", "Chinch bugs"])  # info-only left out
        self.assertEqual(rows[0]["Learn more"], "https://www.wavespestcontrol.com/pest-identifier/sod-webworm/")
        self.assertEqual(rows[0]["Trend"], "Easing next month")
        self.assertEqual(rows[1]["Type"], "Weed")
        self.assertEqual(rows[1]["Trend"], "Starts next month")
        self.assertIsNone(rows[1]["Learn more"])
        self.assertEqual(rows[2]["Trend"], "")

    def test_category_filter_and_info_only(self):
        self.assertEqual([r["Name"] for r in explore.yard_calendar_rows(CALENDAR, categories=["weed"])], ["Winter weeds"])
        self.assertEqual(len(explore.yard_calendar_rows(CALENDAR, include_info_only=True)), 4)

    def test_year_rows(self):
        rows = explore.yard_year_rows(CALENDAR)
        self.assertEqual(rows[1]["Name"], "Tropical sod webworm")
        self.assertEqual([rows[1][m] for m in ("Aug", "Sep", "Dec")], [1, 3, 1])
        self.assertEqual(list(rows[0])[:3], ["Name", "Jan", "Feb"])

    def test_plan_ahead_and_links(self):
        self.assertEqual(explore.plan_ahead(CALENDAR), ["Winter weeds are still in the pre-emergent window."])
        self.assertEqual(explore.plan_ahead({}), [])
        self.assertIsNone(explore.absolute_url("javascript:alert(1)"))
        self.assertIsNone(explore.absolute_url("//evil.example/x"))
        self.assertEqual(explore.absolute_url("https://example.com/a"), "https://example.com/a")


class PressureIndex(unittest.TestCase):
    def test_rating_label_uses_the_scale(self):
        self.assertEqual(explore.rating_label(2.2, INDEX["scale"]), "Low")
        self.assertEqual(explore.rating_label(2.5, INDEX["scale"]), "Moderate")
        self.assertEqual(explore.rating_label(0), "None")
        self.assertEqual(explore.rating_label(9), "High")

    def test_rows_busiest_first(self):
        rows = explore.pressure_index_rows(INDEX)
        self.assertEqual([r["County"] for r in rows], ["Sarasota", "Manatee"])
        self.assertEqual(rows[1], {"County": "Manatee", "Service": "Pest", "Visits": 54, "Average (0 to 5)": 2.2, "Median": 1.5, "Rating": "Low"})
        self.assertEqual(explore.pressure_index_rows({}), [])

    def test_caption(self):
        text = explore.pressure_index_caption(INDEX)
        self.assertIn("from 2026-09-24 to 2026-11-01", text)
        self.assertIn("20 or more visits", text)
        self.assertIn("1 smaller group is left out", text)
        self.assertIn("CC BY 4.0", text)
        self.assertNotIn("left out", explore.pressure_index_caption(dict(INDEX, hidden_groups=0)))


class FriendlyErrors(unittest.TestCase):
    def test_messages(self):
        self.assertIn("busy", explore.friendly_error(api.WavesApiError(429)))
        self.assertIn("weather data", explore.friendly_error(api.WavesApiError(503)))
        self.assertIn("could not use that choice: That ZIP is not in Florida.", explore.friendly_error(api.WavesApiError(400, "unsupported_zip", "That ZIP is not in Florida.")))
        self.assertIn("had a problem", explore.friendly_error(api.WavesApiError(500)))
        self.assertIn("Could not reach", explore.friendly_error(urllib.error.URLError("down")))
        self.assertIn("Could not reach", explore.friendly_error(TimeoutError()))
        self.assertIn("Something went wrong", explore.friendly_error(KeyError("x")))


if __name__ == "__main__":
    unittest.main()
