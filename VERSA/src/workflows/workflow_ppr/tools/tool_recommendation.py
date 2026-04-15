import json
import logging
import re
import textwrap

import pandas as pd
import streamlit as st
try:
    from langchain_core.tools import BaseTool
except ImportError:
    from langchain.tools import BaseTool
from pandas import DataFrame

from src.common.workflow_context import get_workflow
from src.utils.versa_paths import load_workflow_csv
from ..cache import cache_product


class ProductRecommendation(BaseTool):
    name: str = "product_recommendation"
    description: str = ("Use this tool when you need to do product recommendation. To use the tool, you do not need to give any parameter.")
    
    def _run(self) -> str:
        workflow = get_workflow()
        if not workflow:
            return "Error: workflow context not available."
        memory = workflow['workflow_memory']
        logo_name = memory.logo_name
        category = memory.category or memory.category_recommendation
        if not category or not logo_name:
            return (
                "Cannot run product recommendation: category or logo name is missing. "
                "Please confirm or select a category first, then try again."
            )
        if not memory.category and memory.category_recommendation:
            memory.category = category
        slugger_file = cache_product()
        slugger_file = slugger_file[slugger_file['CATEGORY'].str.lower() == str(category).lower()]

        try:
            # Step 1. Get the number of recommendations
            logging.info(f"* Pull recommendations for : logo_name-{logo_name}, category-{category}")
            num_of_recommendations = st.secrets.ppr.num_of_recommendations
            
            # Step 2. Get recommendation from database
            all_available_products = _fetch_recommendation_list_from_SF(logo_name, category)
            if all_available_products.empty:
                raise ValueError(f"No recommendations found for {category} category with logo name {logo_name}")
            
            # Step 3. Adjust rank to include new products in top k
            try:
                all_available_products = _promote_new_product(
                    all_available_products, 
                    k=num_of_recommendations
                )
            except Exception as e:
                # use original recommendations if error occurs
                logging.error(f"Error while promoting new products: {e}")
                all_available_products = all_available_products['ITEM_ID']
            
            # add new rank
            all_available_products = pd.DataFrame(all_available_products, columns=['ITEM_ID'])
            all_available_products['RANK'] = range(len(all_available_products))
            # Step 4, Join with product table to get product details
            all_available_products = pd.merge(
                slugger_file,
                all_available_products, 
                on='ITEM_ID', 
                how='outer',
                indicator=True
            )
            # restore the rank + fill na with
            all_available_products.sort_values(by='RANK', inplace=True)
            all_available_products['RANK'] = range(len(all_available_products))

            all_available_products['_merge'] = all_available_products['_merge'].map({
                'left_only': False,
                'right_only': True,
                'both': False
            })
            all_available_products = all_available_products.rename(columns={'_merge': 'FROM_SLUGGER'})
        
            # Step 4. Drop unnecessary columns
            all_available_products.drop(
                columns=['CATEGORY', 'LOGO', 'IS_NEW'], 
                inplace=True, 
                errors='ignore'
            )
            
            recommendations = all_available_products.head(num_of_recommendations)
            
            return self._on_success(all_available_products, recommendations)
        except ValueError as e:
            logging.error(f"Error processing recommendations, param-category-{category}, param-logo_name-{logo_name}", exc_info=True)
            return self._on_error()
        

    def _arun(self) -> str:
        raise NotImplementedError("This tool does not support async")
    
    def _on_success(self, all_available_products, recomendations):
        workflow = get_workflow()
        if not workflow:
            return "Error: workflow context not available."
        memory = workflow["workflow_memory"]
        memory.recommendations = recomendations
        memory.all_available_products = all_available_products
        memory.filtered_products = all_available_products
        to_next = workflow["to_next_memory"]
        to_next.reset()
        to_next.decision = "SUCCESS"
        to_next.source = self.name
        # Brief tool text for the model; the chat UI appends the full product table to the assistant message.
        n_full = len(all_available_products) if all_available_products is not None else 0
        to_next.message = (
            f"Successfully loaded {n_full} product row(s) for category {getattr(memory, 'category', '')!r} "
            f"(logo {getattr(memory, 'logo_name', '')!r}). "
            "The user sees the **full** recommendation table in the chat after your reply—give a short intro only; "
            "do not invent SKUs or re-list every line in prose."
        )
        logging.info(f"* Sucessfully get the recommendations.")
        return to_next.message

    def _on_error(self) -> str:
        workflow = get_workflow()
        if not workflow:
            return "An error occurred while getting recommendation."
        to_next = workflow['to_next_memory']
        to_next.reset()
        to_next.decision = "ERROR"
        to_next.source = self.name
        to_next.message = f"An error occurred while getting recommendation."
        return to_next.message


# =============================================================================
# DATA HANDLING
# =============================================================================
def _fetch_recommendation_list_from_SF(logo_name, category) -> DataFrame:
    """
    Fetches recommended product data for a given logo and category.
    If no matching logo is found, defaults to 'default' logo.
    """
    # logo_name = logo_name.replace("'", "''")
    # query = textwrap.dedent("""\
    #     SELECT
    #         *
    #     FROM 
    #         {recommendation_table}
    #     WHERE
    #         (LOWER(LOGO) = LOWER('{logo_name}') AND LOWER(CATEGORY) = LOWER('{category}'))
    #         OR
    #         (LOWER(LOGO) = 'default' AND LOWER(CATEGORY) = LOWER('{category}') AND NOT EXISTS (
    #             SELECT 1 FROM {recommendation_table} WHERE LOWER(LOGO) = LOWER('{logo_name}') AND LOWER(CATEGORY) = LOWER('{category}')
    #         ))
    #     ORDER BY
    #         RANK
    #     """).format(
    #         recommendation_table=st.secrets.ppr.table.recommendation_table,
    #         logo_name=logo_name,
    #         category=category
    #     )
    # conn = st.connection("snowflake")
    # return conn.query(query)
    df = load_workflow_csv("ppr_recommendation.csv")
    
    return df[df['CATEGORY'].str.lower() == category.lower()]



def _promote_new_product(recommendations: DataFrame, k: int) -> DataFrame:
    # Step 1: if not new product, keep the item code and return
    if not recommendations['IS_NEW'].any():
        return recommendations['ITEM_ID']  # No new products to promote

    # Step 2: Calculate the number of promotions required
    # If there are already 2 new products in the top k, no promotions are required
    num_promotion = max(0, 2 - recommendations.head(k)['IS_NEW'].sum())
    
    if num_promotion == 0:
        return recommendations['ITEM_ID']
    elif num_promotion == 1:
        new_products_to_promote = recommendations[
            ~recommendations.index.isin(recommendations.head(k).index) & recommendations['IS_NEW']
        ]
        
        # Find the rank of the existing new product in the top k, if any
        existing_new_product = recommendations[recommendations['IS_NEW']].head(k)
        existing_new_product_rank = existing_new_product.iloc[0]['RANK']

        if existing_new_product_rank != k:
            # if the existing new product is not at rank k, promote the next new product to k
            promote_strategy = [(k, new_products_to_promote.index[0])]
        else:
            # if the existing new product is at rank k, promote the new product to k-1
            promote_strategy = [
                (k - 1, recommendations.head(k).query('IS_NEW').index[0]),
                (k - 1, new_products_to_promote.index[0])
            ]
    elif num_promotion == 2:
        new_products_to_promote = recommendations[
            ~recommendations.index.isin(recommendations.head(k).index) & recommendations['IS_NEW']
        ]
        promote_strategy = [(k - 1, new_products_to_promote.index[0]), (k - 1, new_products_to_promote.index[1])]
    else:
        raise ValueError("Invalid number of promotions required")

    recommendations['PROMOTED'] = False
    for rank, idx in promote_strategy:
        recommendations.loc[idx, 'RANK'] = rank
        recommendations.loc[idx, 'PROMOTED'] = True
    
    # re-ranking the DataFrame
    recommendations = recommendations.sort_values(by=['RANK', 'PROMOTED'], ascending=[True, False])
    
    # reassing the rank
    recommendations['RANK'] = range(1, len(recommendations) + 1)
    
    return recommendations['ITEM_ID']
