# Southwest Florida Lawn & Pest Explorer

A small [Streamlit](https://streamlit.io/) app on the free Waves public API: this week's
lawn watering plan, this month's pest pressure forecast, the yard pressure calendar and
the county Pest Pressure Index. Pick a city, a grass and a month in the sidebar.

```sh
pip install -r apps/streamlit/requirements.txt
streamlit run apps/streamlit/streamlit_app.py
```

The app adds the repository's `python/src` to the import path, so it runs without
`pip install waves-lawn-tools`. Answers are cached for an hour. Data from the free
[Waves public API](../../docs/public-api.md); each section links to its page on
[wavespestcontrol.com](https://www.wavespestcontrol.com/).
