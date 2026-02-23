import streamlit as st
from pandas import DataFrame

from src.utils.versa_paths import load_workflow_pickle


# FETCH_DISTRIBUTOR = """
# SELECT
#     PCNA_ID as DISTRIBUTOR_ID,
#     ACCOUNT_NAME as DISTRIBUTOR_NAME,
#     ALL_ACCOUNT_NAMES as DISTRIBUTOR_USED_NAME
# FROM
#     {distributor_table}
# """


@st.cache_data(show_spinner="Loading Distributor Data...")
def cache_distributor() -> DataFrame:
    # query = FETCH_DISTRIBUTOR.format(
    #     distributor_table=st.secrets.mpr.table.distributor_table
    # )
    # conn = st.connection("snowflake")
    # return conn.query(query)
    return load_workflow_pickle("distributors.pkl")