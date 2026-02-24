import logging
import textwrap
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st
try:
    from langchain_core.tools import BaseTool
except ImportError:
    from langchain.tools import BaseTool
from pandas import DataFrame

from src.common.workflow_context import get_workflow


class AnalyzeYOY(BaseTool):
    name: str = "analyze_yoy"
    description: str = "Use this tool to analyze yoy sales. To use the tool, you must provide a logo name, a distributor name, and a category name."

    def _run(self, logo_name=None, distributor_name=None, category=None):
        workflow = get_workflow()
        if not workflow:
            return "Error: workflow context not available."
        memory = workflow['workflow_memory']
        distributor_name = memory.distributor_name
        logo_name = memory.logo_name
        category = memory.category
        try:
            analysis = year_over_year_analysis(logo_name, distributor_name, category)
            return self._on_success(analysis)
        except Exception as e:
            logging.error(f"Error while analyze logo sales", exc_info=True)
            return self._on_error(logo_name)

    def _arun(self, logo_name, distributor_name, category) -> str:
        raise NotImplementedError("This tool does not support async")
    
    def _on_success(self, analysis) -> str:
        workflow = get_workflow()
        if not workflow:
            return "Error: workflow context not available."
        memory = workflow['workflow_memory']
        memory.yoy_analysis = analysis
        to_next = workflow['to_next_memory']
        to_next.reset()
        to_next.decision = "SUCCESS"
        to_next.source = self.name
        to_next.message = f"Sucessfully analyzed logo sales."
        return to_next.message

    def _on_error(self, logo_name: str) -> str:
        workflow = get_workflow()
        if not workflow:
            return "An error occurred while analyzing the logo sales."
        to_next = workflow['to_next_memory']
        to_next.reset()
        to_next.decision = "ERROR"
        to_next.source = self.name
        to_next.message = f"An error occurred while analyzing the logo sales."
        return to_next.message


def _fetch_yoy_sales_data(distributor_name: str, logo_name: str, category: str) -> DataFrame:
    logo_name = logo_name.replace("'", "''")
    query = textwrap.dedent(f"""\
        SELECT
            *
        FROM 
            DEV_DW.FKPI.RECURRING_SALES_TMP
        WHERE 
            LOWER(DISTRIBUTOR) = LOWER('{distributor_name}') AND
            LOWER(LOGO) = LOWER('{logo_name}') AND
            LOWER(CATEGORY) = LOWER('{category}') AND
            INVDATE > DATEADD(YEAR, -2, CURRENT_DATE()) AND
            IS_RECURRING_ORDER = 1
        """)
    
    conn = st.connection("snowflake")
    df = conn.query(query)
    
    df.to_csv("yoy.csv")
    return df


def year_over_year_analysis(distributor_name, logo_name, category) -> str:
    """
    Performs a year-over-year sales analysis.

    Returns:
    str or None: Formatted growth rate as a string: +/-X%, or None if insufficient data.
    """
    # Fetch sales data
    df = _fetch_yoy_sales_data(distributor_name, logo_name, category)

    # Ensure INVDATE is in datetime format
    df['INVDATE'] = pd.to_datetime(df['INVDATE'])

    # Define the current and previous year periods
    end_date = datetime.now()
    start_date_current_year = end_date - timedelta(days=365)
    start_date_previous_year = start_date_current_year - timedelta(days=365)

    # Filter data for the current and previous year periods
    current_year_sales = df[(df['INVDATE'] >= start_date_current_year) & (df['INVDATE'] < end_date)]['REC_REVENUE'].sum()
    previous_year_sales = df[(df['INVDATE'] >= start_date_previous_year) & (df['INVDATE'] < start_date_current_year)]['REC_REVENUE'].sum()

    # Check for zero sales in either year
    if current_year_sales == 0 or previous_year_sales == 0:
        return None

    # Calculate the year-over-year growth rate as an integer
    growth_rate = (current_year_sales - previous_year_sales) / previous_year_sales
    return f"{growth_rate:+.0%}"
