"""Silabus dashboard.

Nothing to plot until `make ingest` has run, so the page says that instead of
drawing an empty chart.
"""

import streamlit as st

st.set_page_config(page_title="Silabus", page_icon="📚", layout="wide")

st.title("Silabus")
st.caption("Skill demand in Indonesian tech job postings.")

st.info(
    "No data yet. Run `make up && make migrate`, then `make ingest SOURCE=fixtures`, "
    "then reload this page."
)

st.markdown(
    """
Once there is data this page should show:

1. Top 20 skills per role family, filterable by city and work mode.
2. The denominator next to every number, e.g. "38% of 412 backend postings in Jakarta".
3. A seniority split.
"""
)
