import textwrap

import pandas as pd
import streamlit as st
from pandas import DataFrame

from src.utils.versa_paths import load_workflow_pickle


FETCH_NAICS_CODE = """
SELECT
    DISTINCT naics_code
FROM {recommendation_table}
ORDER BY naics_code
"""


@st.cache_data(show_spinner="Loading Industry Data...")
def cache_naics_code() -> DataFrame:
    # # load mapping table
    # mapping = pd.read_csv(st.secrets.ipr.table.naics_code_to_industry)
    # mapping['NAICS_CODE'] = mapping['NAICS_CODE'].astype(str)
    
    # # load all available NAICS codes from recommendation table
    # naics_codes = _fetch_naics_list_from_SF()
    # naics_codes['NAICS_CODE'] = naics_codes['NAICS_CODE'].astype(str)

    # # merge the two tables
    # df = pd.merge(naics_codes, mapping, on='NAICS_CODE', how='inner')
    # return df
    return load_workflow_pickle("naics_code.pkl")


def _fetch_naics_list_from_SF() -> DataFrame:
    """
    Fetches recommended product data for a given logo and category.
    If no matching logo is found, defaults to 'default' logo.
    """
    query = FETCH_NAICS_CODE.format(recommendation_table=st.secrets.ipr.table.recommendation_table)
    conn = st.connection("snowflake")
    return conn.query(query)