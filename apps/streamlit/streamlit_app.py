"""Southwest Florida Lawn & Pest Explorer.

A small Streamlit app on the free Waves public API: this week's lawn watering plan,
this month's pest pressure forecast, the yard pressure calendar and the county Pest
Pressure Index. No key, no sign-up, no database.

Run it from the repository:

    pip install -r apps/streamlit/requirements.txt
    streamlit run apps/streamlit/streamlit_app.py

It adds the repository's python/src to the import path, so it runs before and without the
PyPI release (pip install waves-lawn-tools).

Code: https://github.com/wavespestcontrolfl/waves-lawn-tools
MIT License. Copyright (c) 2026 Waves Pest Control, LLC.
"""

import datetime
import sys
from pathlib import Path

import streamlit as st

_SRC = Path(__file__).resolve().parents[2] / "python" / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from waves_lawn_tools import api, explore  # noqa: E402

REPO_URL = "https://github.com/wavespestcontrolfl/waves-lawn-tools"
API_DOCS_URL = REPO_URL + "/blob/main/docs/public-api.md"
DEFAULT_CITY = "bradenton-fl"
CACHE_SECONDS = 3600  # the API says the data changes a few times a day at most


# The API asks callers to cache: one hour here, so a busy app stays far below 120 calls per 15 minutes.
@st.cache_data(ttl=CACHE_SECONDS, show_spinner=False)
def load_locations():
    return api.get_pest_forecast_locations()


@st.cache_data(ttl=CACHE_SECONDS, show_spinner=False)
def load_watering_plan(location, grass):
    return api.get_watering_plan(location=location, grass=grass)


@st.cache_data(ttl=CACHE_SECONDS, show_spinner=False)
def load_pest_forecast(location):
    return api.get_pest_forecast(location=location)


@st.cache_data(ttl=CACHE_SECONDS, show_spinner=False)
def load_yard_calendar(month, grass):
    return api.get_yard_calendar(month=month, grass=grass)


@st.cache_data(ttl=CACHE_SECONDS, show_spinner=False)
def load_pressure_index():
    return api.get_pest_pressure_index()


def show_error(error):
    st.warning(explore.friendly_error(error))


def section_header(title, page_url, link_text):
    st.subheader(title)
    st.markdown(f"[{link_text}]({page_url})")


def watering_section(city, city_label, grass):
    section_header("This week's watering plan", explore.WATERING_PAGE, "Open the full Lawn Watering Calculator")
    try:
        plan = load_watering_plan(city, explore.watering_grass_value(grass))
    except Exception as error:  # a friendly message, never a traceback, for the visitor
        show_error(error)
        return
    text = explore.watering_plan_text(plan)
    st.markdown(f"**{text['headline'] or city_label}**")
    if text["action"]:
        st.write(text["action"])
    facts = explore.watering_plan_facts(plan)
    if facts:
        st.table([{"Fact": label, "Value": value} for label, value in facts])
    for note in text["notes"]:
        st.caption(note)
    if plan.get("rulesUrl"):
        st.caption(f"Local rules always come first: [water management district rules]({plan['rulesUrl']}).")
    if plan.get("disclaimer"):
        st.caption(plan["disclaimer"])


def forecast_section(city, city_label):
    section_header("This month's pest pressure forecast", explore.FORECAST_PAGE, "Open the Pest Pressure Forecast")
    try:
        forecast = load_pest_forecast(city)
    except Exception as error:
        show_error(error)
        return
    summary = explore.pest_forecast_summary(forecast)
    st.markdown(f"**{summary['month']} in {city_label}.** {summary['summary']}")
    if summary["weather"]:
        st.caption(summary["weather"])
    rows = explore.pest_forecast_rows(forecast)
    if rows:
        st.dataframe(rows, hide_index=True)
    if summary["disclaimer"]:
        st.caption(summary["disclaimer"])


def calendar_section(month, grass):
    section_header(
        f"Yard pressure calendar: {explore.month_name(month)}, {explore.grass_label(grass)}",
        explore.YARD_CALENDAR_PAGE,
        "Open the Lawn & Landscape Calendar",
    )
    try:
        calendar = load_yard_calendar(month, explore.calendar_grass_code(grass))
    except Exception as error:
        show_error(error)
        return
    for line in explore.plan_ahead(calendar):
        st.info(line)
    rows = explore.yard_calendar_rows(calendar)
    if rows:
        st.dataframe(
            rows,
            hide_index=True,
            column_config={"Learn more": st.column_config.LinkColumn("Learn more", display_text="Open")},
        )
        st.caption("Level: 3 peak season, 2 in season, 1 low, 0 off season.")
        with st.expander("Level for every month of the year"):
            st.dataframe(explore.yard_year_rows(calendar), hide_index=True)
    else:
        st.write("Nothing is listed for that month and grass.")


def index_section():
    section_header("Pest Pressure Index by county", explore.INDEX_PAGE, "Open the Pest Pressure Index")
    try:
        index = load_pressure_index()
    except Exception as error:
        show_error(error)
        return
    rows = explore.pressure_index_rows(index)
    if rows:
        st.dataframe(rows, hide_index=True)
    else:
        st.write("No county has enough visits in the window yet.")
    st.caption(explore.pressure_index_caption(index))
    if index.get("citation"):
        st.caption(f"Cite: {index['citation']}")


def main():
    st.set_page_config(page_title="Southwest Florida Lawn & Pest Explorer", page_icon="💧", layout="wide")
    st.title("Southwest Florida Lawn & Pest Explorer")
    st.write(
        "Pick a city, a grass and a month. See this week's watering plan, the pest outlook, "
        "what is active in yards, and how busy technicians find pests by county."
    )

    with st.sidebar:
        st.header("Your yard")
        try:
            choices = explore.location_choices(load_locations())
        except Exception as error:
            show_error(error)
            choices = [(DEFAULT_CITY, "Bradenton, FL")]
        slugs = [slug for slug, _ in choices]
        labels = dict(choices)
        city = st.selectbox(
            "City",
            slugs,
            index=slugs.index(DEFAULT_CITY) if DEFAULT_CITY in slugs else 0,
            format_func=lambda slug: labels.get(slug, slug),
        )
        grass_values = [watering for watering, _, _ in explore.GRASS_TYPES]
        grass = st.selectbox("Grass type", grass_values, format_func=explore.grass_label)
        today = datetime.date.today()
        month = st.selectbox(
            "Month",
            list(range(1, 13)),
            index=today.month - 1,
            format_func=explore.month_name,
        )
        st.caption("Answers are cached for an hour.")

    city_label = labels.get(city, city)
    watering_section(city, city_label, grass)
    st.divider()
    forecast_section(city, city_label)
    st.divider()
    calendar_section(month, grass)
    st.divider()
    index_section()

    st.divider()
    st.caption(
        f"Data from the free [Waves public API]({API_DOCS_URL}). "
        f"Code on [GitHub]({REPO_URL}) (MIT). "
        "Forecasts and calendars are seasonal, weather-based models, not measurements; "
        "your local watering rules come first. "
        "By [Waves Pest Control & Lawn Care](https://www.wavespestcontrol.com/)."
    )


main()
