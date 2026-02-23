import pandas as pd
import streamlit as st
from pandas import DataFrame

from src.utils.versa_paths import load_workflow_pickle


FETCH_LOGO = """
SELECT
    LOGO as CLIENT_NAME,
    TRANSACTION_COUNT,
    HAS_RECURRING_REVENUE
FROM
    {logo_table}
"""


@st.cache_data(show_spinner="Loading Client Data...")
def cache_logo() -> DataFrame:
    # query = FETCH_LOGO.format(
    #     logo_table=st.secrets.ppr.table.logo_table
    # )
    # conn = st.connection("snowflake")
    # df = conn.query(query)
    return load_workflow_pickle("logo.pkl")
