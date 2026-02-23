import logging
import textwrap
from datetime import datetime, timedelta
from typing import Tuple, List

import numpy as np
import pandas as pd
try:
    from langchain_core.tools import BaseTool
except ImportError:
    from langchain.tools import BaseTool
from pandas import DataFrame, Series

from src.common.workflow_context import get_workflow
from src.utils.versa_paths import load_workflow_pickle


class AnalyzeLogoSales(BaseTool):
    name: str = "analyze_logo_sales"
    description: str = "Use this tool to analyze logo sales. To use the tool, you must provide a logo name and a distributor name."

    def _run(self, logo_name=None, distributor_name=None):
        workflow = get_workflow()
        if not workflow:
            return "Error: workflow context not available."
        memory = workflow['workflow_memory']
        distributor_name = memory.distributor_name
        logo_name = memory.logo_name
        distributor_used_name = memory.distributor_used_name
        try:
            analysis_date, analysis = _logo_sales_analysis(logo_name, distributor_name, distributor_used_name)
            return self._on_success(analysis_date, analysis)
        except Exception as e:
            logging.error(f"Error while analyze logo sales", exc_info=True)
            return self._on_error(logo_name)

    def _arun(self, logo_name: str, distributor_name: str) -> str:
        raise NotImplementedError("This tool does not support async")
    
    def _on_success(self, analysis_date, analysis) -> str:
        workflow = get_workflow()
        if not workflow:
            return "Sucessfully analyzed logo sales."
        memory = workflow['workflow_memory']
        memory.logo_sales_analysis_date = analysis_date
        memory.logo_sales_analysis = analysis
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


# =============================================================================
# DATA HANDLING
# =============================================================================
def _fetch_logo_sales_data(logo_name: str) -> DataFrame:
    """
    Fetches logo sales data for the past two years, including recurring revenue and special(sample) orders.
    """
    # logo_name = logo_name.replace("'", "''")
    # query = textwrap.dedent("""\
    #     SELECT
    #         *
    #     FROM 
    #         {table_name}
    #     WHERE 
    #         LOWER(LOGO) = LOWER('{logo_name}')
    #     """).format(
    #         table_name=st.secrets["ppr"]["table"]["logo_sales_table"],
    #         logo_name=logo_name,
    #     )
    # conn = st.connection("snowflake")
    # df = conn.query(query)
    
    return load_workflow_pickle("logo_sales_data.pkl")


def _extract_sales_data_within_timeframe(data: DataFrame, start_date: datetime, end_date: datetime, distributor_names: List[str], mri_group: list) -> Tuple[Series, Series]:
    # Filter data within the given timeframe
    timeframe_data = data[(data['INVDATE'] > start_date) & (data['INVDATE'] <= end_date)]
    
    # Filter data for the given distributor names
    distributor_sales_data = timeframe_data[
        timeframe_data['DISTRIBUTOR'].str.lower().isin([name.lower() for name in distributor_names])
    ]
    
    # Sum sales for the given distributor by MRIGROUP
    distributor_sales = distributor_sales_data.groupby('MRIGROUP')['SALES_AMOUNT'].sum().reindex(mri_group, fill_value=0.00).round(2)
    # Calculate total sales for the given distributor
    distributor_sales['Total'] = distributor_sales.sum()

    # Sum sales for the given logo for all distributors by MRIGROUP
    logo_sales = timeframe_data.groupby('MRIGROUP')['SALES_AMOUNT'].sum().reindex(mri_group, fill_value=0.00).round(2)
    # Calculate total sales for the given logo
    logo_sales['Total'] = logo_sales.sum()

    return distributor_sales, logo_sales


def _calculate_yoy_change(this_year_sales: Series, last_year_sales: Series) -> Series:
    # Calculate the YOY change for each category
    yoy_change = (this_year_sales - last_year_sales) / last_year_sales.where(last_year_sales != 0, np.nan)

    # Replace infinite values with NaN and then with 'N/A'
    yoy_change.replace([np.inf, -np.inf], np.nan, inplace=True)

    # Format the YOY change as percentage with no decimal places and add the sign
    yoy_change_percentage = yoy_change.apply(lambda x: f"{x:+.0%}" if pd.notnull(x) is True else 'N/A')
    return yoy_change_percentage


def _calculate_sales_percent(sales_amount, total_sales) -> str:
    """
    Calculate the sales percentage.
    """
    if total_sales != 0:
        sales_percent = sales_amount / total_sales * 100
        return f"{sales_percent:.0f}%"
    else:
        return 'N/A'
    

def _logo_sales_analysis(logo_name: str, distributor_name: str, distributor_used_name: list):
    def _format_value(val):
        """
        Function to convert and format values
        """
        try:
            # Attempt to convert to float and format
            return f"{float(val):,.0f}"
        except ValueError:
            # Return the value as-is if it's not a number
            return val

    # Load the transaction data
    data = _fetch_logo_sales_data(logo_name)
    
    refresh_date = pd.to_datetime(data['LATEST_INVOICE_DATE'].iloc[0])
    start_date_this_year = refresh_date - pd.DateOffset(years=1)
    start_date_last_year = start_date_this_year - pd.DateOffset(years=1)

    data['INVDATE'] = pd.to_datetime(data['INVDATE'])
    data['SALES_AMOUNT'] = data['SALES_AMOUNT'].astype(float).round(2)
    table_columns = ['Misc.','Apparel', 'Bags', 'Drinkware', 'Home & Outdoor', 'Stationery', 'Technology', 'Total', 'Sales %']
    mri_group = table_columns[:-2]

    # Filter distributor_names to include only those with sales
    distributor_with_sales = data['DISTRIBUTOR'].unique()
    filtered_distributor_names = [name for name in distributor_used_name if name in distributor_with_sales]

    # Extract data for the last 12 months
    this_year_distributor_sales, this_year_logo_sales = _extract_sales_data_within_timeframe(data, start_date_this_year, refresh_date, filtered_distributor_names, mri_group)
    # Extract data for the previous year
    last_year_distributor_sales, last_year_logo_sales = _extract_sales_data_within_timeframe(data, start_date_last_year, start_date_this_year, filtered_distributor_names, mri_group)
    
    # Calculate YOY change
    distributor_yoy = _calculate_yoy_change(this_year_distributor_sales, last_year_distributor_sales)
    logo_yoy = _calculate_yoy_change(this_year_logo_sales, last_year_logo_sales)

    # Calculate [count] of distributor for this year
    timeframe_data = data[(data['INVDATE'] > start_date_this_year) & (data['INVDATE'] <= refresh_date)]
    other_distributor_count = timeframe_data['DISTRIBUTOR'].nunique() - len(filtered_distributor_names)

    # Prepare data for the result DataFrame
    other_distributor_sales = this_year_logo_sales - this_year_distributor_sales
    
    this_year_distributor_sales['Sales %'] = _calculate_sales_percent(
        this_year_distributor_sales['Total'],
        this_year_logo_sales['Total']
    )
    
    other_distributor_sales['Sales %'] = _calculate_sales_percent(
        other_distributor_sales['Total'],
        this_year_logo_sales['Total']
    )
    
    this_year_logo_sales['Sales %'] = '100%'
    distributor_yoy['Sales %'] = 'N/A'
    logo_yoy['Sales %'] = 'N/A'

    # Format the result
    index_labels = [
        f'{distributor_name}',
        f'All {other_distributor_count} Other Distributors',
        f'Total {logo_name.upper()}',
        f'YOY {distributor_name}',
        f'YOY Total {logo_name.upper()}'
    ]

    # Convert each Series to DataFrame with the specified columns
    dfs = []
    for series, label in zip(
            [this_year_distributor_sales, other_distributor_sales, this_year_logo_sales, distributor_yoy, logo_yoy],
            index_labels):
        df = series.reindex(table_columns).to_frame().T  # Reindex and transpose
        df.index = [label]  # Set custom index label
        dfs.append(df)

    # Concatenate the DataFrames vertically
    concatenated_df = pd.concat(dfs)
    for column in concatenated_df.columns:
        concatenated_df[column] = concatenated_df[column].apply(_format_value)
    
    return refresh_date.strftime("%B %d, %Y"), concatenated_df
