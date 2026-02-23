import hashlib
import logging
import random
import textwrap

import pandas as pd
import streamlit as st
try:
    from langchain_core.tools import BaseTool
except ImportError:
    from langchain.tools import BaseTool

from src.common.workflow_context import get_workflow
from ..cache import cache_logo


class RecommendCategory(BaseTool):
    name: str = "recommend_category"
    description: str = ("Use this tool when you need to recommend the category. To use the tool, you must provide both logo name and distributor name.")
    
    def _run(self, logo_name=None, distributor_name=None) -> str:
        workflow = get_workflow()
        if not workflow:
            return "Error: workflow context not available."
        memory = workflow['workflow_memory']
        distributor_name = memory.distributor_name
        logo_name = memory.logo_name
        try:
            logging.info(f"* Recommend category with: {logo_name}, {distributor_name}")
            has_recurring = memory.has_recurring
            if has_recurring:
                category = _random_pick_category(logo_name, distributor_name)
            else:
                category = _random_pick_category(logo_name, distributor_name)
            return self._on_success(category)
        except Exception as e:
            logging.error(f"Error while validating logo name param-logo_name-{logo_name}", exc_info=True)
            return self._on_error(logo_name, distributor_name)

    def _arun(self, logo_name: str, distributor_name: str) -> str:
        raise NotImplementedError("This tool does not support async")
    
    def _on_success(self, category) -> str:
        workflow = get_workflow()
        if not workflow:
            return "Error: workflow context not available."
        memory = workflow['workflow_memory']
        memory.category_recommendation = category
        to_next = workflow['to_next_memory']
        to_next.reset()
        to_next.decision = "SUCCESS"
        to_next.source = self.name
        to_next.message = f"Sucessfully recommended the category."
        return to_next.message

    def _on_error(self, logo_name: str, distributor_name: str) -> str:
        workflow = get_workflow()
        if not workflow:
            return f"An error occurred while recommending category with {logo_name}, {distributor_name}."
        to_next = workflow['to_next_memory']
        to_next.reset()
        to_next.decision = "ERROR"
        to_next.source = self.name
        to_next.message = f"An error occurred while recommending category with {logo_name}, {distributor_name}."
        return to_next.message


# =============================================================================
# DATA HANDLING
# =============================================================================
def _fetch_industry_sales_data(categories, logo_name):
    """
    Fetches industry sales data for NAICS codes associated with a given logo in the past one year.
    """
    # SQL query with CTE to fetch sales data

    # List of categories to include
    # logo_name = logo_name.replace("'", "''")
    # formatted_categories = ', '.join([f"'{category}'" for category in categories])

    # query = textwrap.dedent("""\
    #     WITH naics_code AS (
    #         SELECT DISTINCT NAICSCODE
    #         FROM {table_name}
    #         WHERE LOWER(LOGO) = LOWER('{logo_name}') AND INVDATE > DATEADD(YEAR, -1, CURRENT_DATE())
    #     )
        
    #     SELECT
    #         s.*
    #     FROM 
    #         {table_name} s
    #     INNER JOIN naics_code n
    #         ON s.NAICSCODE = n.NAICSCODE
    #     WHERE 
    #         LOWER(s.CATEGORY) IN ({formatted_categories})
    #         AND s.INVDATE > DATEADD(YEAR, -1, CURRENT_DATE())
    #         AND s.IS_RECURRING_ORDER = 1
    #     """).format(
    #         table_name=st.secrets['ppr']['table']['recurring_sales_table'],
    #         logo_name=logo_name,
    #         formatted_categories=formatted_categories
    #     )

    # conn = st.connection("snowflake")
    # df = conn.query(query)
    # return df
    pass


def _fetch_logo_transactions(categories, logo_name: str):
    """
    Fetches transaction data for given logo (non recurring logo) in the past one year.
    """
    # SQL query with CTE to fetch sales data

    # List of categories to include
    # logo_name = logo_name.replace("'", "''")
    # formatted_categories = ', '.join([f"'{category}'" for category in categories])

    # query = textwrap.dedent("""\
    #     SELECT
    #         *
    #     FROM 
    #         {table_name}
    #     WHERE
    #         LOWER(LOGO) = LOWER('{logo_name}')
    #         AND LOWER(CATEGORY) IN ({formatted_categories})
    #         AND INVDATE > DATEADD(YEAR, -1, CURRENT_DATE())
    #     """).format(
    #         table_name=st.secrets['ppr']['table']['recurring_sales_table'],
    #         logo_name=logo_name,
    #         formatted_categories=formatted_categories
    #     )

    # conn = st.connection("snowflake")
    # df = conn.query(query)
    # return df
    pass


def _random_pick_category(logo_name, distributor_name):
    seed_string = f"{logo_name}_{distributor_name}"
    hashed_seed = int(hashlib.sha256(seed_string.encode('utf-8')).hexdigest(), 16)
    random.seed(hashed_seed)
    
    categories = list(st.secrets['ppr']['categories'].keys())
    chosen_category = random.choice(categories)
    return chosen_category


def _identify_non_dominant_categories(distributor_sales_by_category, dominance_threshold: int) -> list:
    non_dominant_categories = []

    # Calculate the total sales for each category across all distributors
    total_sales_by_category = distributor_sales_by_category.sum()

    # Iterate through each category present in the DataFrame
    for category in distributor_sales_by_category.columns:
        # Calculate the market share for each distributor in the category
        market_shares = distributor_sales_by_category[category] / total_sales_by_category[category] * 100

        # Check if any distributor has a market share exceeding the dominance threshold
        if all(market_share < dominance_threshold for market_share in market_shares):
            non_dominant_categories.append(category)

    return non_dominant_categories


def _industry_gap_analysis(logo_sales, industry_sales) -> str:
    # Aggregate sales per NAICS code, per category
    logo_sales_by_naics_category = logo_sales.groupby(['NAICSCODE', 'CATEGORY'])['REC_REVENUE'].sum().reset_index()

    # Aggregate average sales per NAICS code, per category
    industry_averages_by_naics_category = industry_sales.groupby(['NAICSCODE', 'CATEGORY'])[
        'REC_REVENUE'].mean().reset_index()

    # Merge logo sales with industry averages, ensure all categories from industry averages are included
    merged_data = pd.merge(industry_averages_by_naics_category, logo_sales_by_naics_category,
                           on=['NAICSCODE', 'CATEGORY'], how='left', suffixes=('_industry', '_logo'))

    # Fill missing logo sales with zeros
    merged_data['REC_REVENUE_logo'].fillna(0, inplace=True)

    # Calculate the underpenetration percentage
    merged_data['underpenetration'] = (merged_data['REC_REVENUE_industry'] - merged_data['REC_REVENUE_logo']) / \
                                      merged_data['REC_REVENUE_industry']
    merged_data['gap'] = merged_data['REC_REVENUE_industry'] - merged_data['REC_REVENUE_logo']

    # Find the category/categories with the largest underpenetration in one line
    candidates = merged_data[merged_data['underpenetration'] == merged_data['underpenetration'].max()]

    # Choose the category with the biggest gap if having same underpenetration
    most_underpenetrated_category = candidates.loc[
        candidates['gap'].idxmax(), 'CATEGORY'] if not candidates.empty else None

    return most_underpenetrated_category


def _identify_category_with_largest_gap(distributor: str, non_dominant_categories: list, distributor_sales_by_category) -> str:
    largest_gap = 0
    category_with_largest_gap = None

    # Calculate the total sales for each category across all distributors
    total_sales_by_category = distributor_sales_by_category.sum()

    # Iterate through each non-dominant category to find the largest gap
    for category in non_dominant_categories:
        # Filter for the distributor and category, ensuring the result is a single value
        filtered_sales = distributor_sales_by_category.loc[
            distributor_sales_by_category.index.str.lower() == distributor.lower(), category]

        # Check if the filtered sales is not empty and then extract the first element
        distributor_sales = filtered_sales.iloc[0] if not filtered_sales.empty else 0

        # Calculate the gap
        gap = total_sales_by_category[category] - distributor_sales

        # Check if this gap is the largest found so far
        if gap > largest_gap:
            largest_gap = gap
            category_with_largest_gap = category

    return category_with_largest_gap


def _find_top_sales_category_for_non_recurring_logo(logo_transactions, logo_name):
    """
    Finds the category with the most sales for a given logo.

    Parameters:
    - industry_sales: DataFrame with sales transactions.
    - logo: The logo (company name) to filter by.

    Returns:
    - The category with the most sales for the given logo.
    """
    # Filter the DataFrame
    filtered_df = logo_transactions[logo_transactions['LOGO'].str.lower() == logo_name.lower()]

    # Group by CATEGORY and sum REC_REVENUE, then find the category with the highest sales
    top_category = filtered_df.groupby('CATEGORY')['REVENUE'].sum().idxmax()
    return top_category


def _category_recommendation_for_recurring(logo_name, distributor_name):
    categories = list(st.secrets['ppr']['categories'].keys())
    
    industry_sales = _fetch_industry_sales_data(categories, logo_name)
    
    logo_sales = industry_sales[industry_sales['LOGO'].str.lower() == logo_name.lower()]
    
    if logo_sales is None or logo_sales.empty:
        return _random_pick_category(logo_name, distributor_name)
    
    # Pivot the data to have distributors as rows and categories as columns
    distributor_sales_by_category = logo_sales.pivot_table(
        index='DISTRIBUTOR', 
        columns='CATEGORY',
        values='REC_REVENUE', 
        aggfunc='sum', 
        fill_value=0
    )
    
    # Check if the given distributor is present in the DataFrame
    if distributor_name.lower() not in distributor_sales_by_category.index.str.lower():
        # If not, add a row for the distributor with zeros for each existing category column
        distributor_sales_by_category.loc[distributor_name] = [0] * len(distributor_sales_by_category.columns)
    
    non_dominant_categories = _identify_non_dominant_categories(distributor_sales_by_category, dominance_threshold=60)
    
    if len(non_dominant_categories) > 0:
        chosen_category = _identify_category_with_largest_gap( distributor_name, non_dominant_categories, distributor_sales_by_category)
    else:
        chosen_category = _industry_gap_analysis(logo_sales, industry_sales)

    return chosen_category


def _category_recommendation_for_non_recurring(logo_name, distributor_name):
    """
    Provides a category recommendation along with detailed analysis data.
    """
    categories = list(st.secrets['ppr']['categories'].keys())

    # fetch logo transaction data for the past one year
    logo_transactions = _fetch_logo_transactions(categories, logo_name)

    # if no sales, random pick one category
    if logo_transactions is None or logo_transactions.empty:
        chosen_category = _random_pick_category(logo_name, distributor_name)
    else:
        chosen_category = _find_top_sales_category_for_non_recurring_logo(logo_transactions, logo_name)

    return chosen_category