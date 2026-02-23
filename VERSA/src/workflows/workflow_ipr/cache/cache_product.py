import json
import logging
import os
import re

import pandas as pd
import requests
import streamlit as st
from pandas import DataFrame

from src.utils.versa_paths import load_workflow_pickle


FETCH_PRODUCT = """
SELECT
    *
FROM
    {product_table}
WHERE
    IS_IN_STOCK = TRUE AND
    LOWER(CATEGORY) IN ({formatted_categories})
"""


@st.cache_data(show_spinner="Loading Product Data...", ttl=86400)
def cache_product() -> DataFrame:    
    # categories = st.secrets.ipr.categories.keys()
    # formatted_categories = ', '.join(
    #     [f"'{category}'" for category in categories]
    # )

    # query = FETCH_PRODUCT.format(
    #     product_table=st.secrets.ipr.table.product_table,
    #     formatted_categories=formatted_categories
    #     )
    
    # conn = st.connection("snowflake")
    # products = conn.query(query)
    
    # products['DESCRIPTION'] = products.apply(lambda row: row['DESCRIPTION'].replace('\n', ' '), axis=1)
    # products['PRICE'] = pd.to_numeric(products['PRICE'], errors='coerce')
    # products['REASON'] = products.apply(lambda row: _generate_reason(row), axis=1)
    # products['DOC_STRING'] = products.apply(lambda row: _generate_doc_string(row), axis=1)
    # products['HIGHLIGHTS'] = products.apply(lambda row: _generate_highlights(row), axis=1)
    # products['QUANTITY_BREAK_PRICING'] = products.apply(lambda row: _formate_price_columns(row), axis=1)
    # products['IMAGE_URL'] = products.apply(lambda row: _fetch_images(row), axis=1)
    
    return load_workflow_pickle("products.pkl")


def _generate_reason(row) -> str:
    """
    Generates a reason string for each row.
    """
    formatted_reason = []

    if row['IS_NEW']:
        formatted_reason.append("This product is one of the newest in our range.")

    # Extract the first sentence from the description or use a default message
    if pd.notna(row['DESCRIPTION']) and row['DESCRIPTION'].strip():
        # Extracting the first sentence
        first_sentence = re.split(r'(?<=[.!?]) +', row['DESCRIPTION'])[0]
        formatted_reason.append(first_sentence)

    if not formatted_reason:
        category = row['CATEGORY']
        formatted_reason.append(f"This is a highly rated product in {category}.")

    return ' '.join(formatted_reason)


def _generate_doc_string(row) -> str:
    """
    Generates a string for RAG with product attributes.
    """
    info = f"{row['ITEM_NAME']}."

    if not pd.isna(row['MAIN_MATERIAL']) and row['MAIN_MATERIAL'].strip() != "":
        info += f" The main material is {row['MAIN_MATERIAL']}."

    if not pd.isna(row['BRAND']) and row['BRAND'].strip() != "":
        info += f" The brand is {row['BRAND']}"
    return info


def _generate_highlights(row) -> str:
    """
    Generates a string for highlights in product page.
    """
    highlights = []
    if row['IS_NEW']:
        highlights.append("This product is one of the newest in our range.")
    # Process 'AVAILABLE_COLORS'
    if row.get("DISPLAYED_COLORS") and row["DISPLAYED_COLORS"] != '[]':
        try:
            color_list = json.loads(row['DISPLAYED_COLORS'])
            # Format color string with Oxford comma
            if len(color_list) > 1:
                color_string = ', '.join(color_list[:-1]) + ', and ' + color_list[-1]
            else:
                color_string = color_list[0]
            highlights.append(f"It is available in {color_string} colors.")
        except json.JSONDecodeError:
            pass  # Handle invalid JSON format
    return " ".join(highlights)


def _fetch_images(row):
    url = row['IMAGE_URL']
    item_id = row['ITEM_ID']
    try:
        if not url:
            return None
        
        image_save_path = os.path.join(st.secrets.ipr.product_image_dir, f"{item_id}.jpg")
        if not os.path.exists(image_save_path):
            # Use a session object for connection pooling and reuse
            with requests.Session() as session:
                response = session.get(url, headers={'User-Agent': 'Mozilla/5.0'})
                response.raise_for_status()  # Raises HTTPError for bad responses (4XX or 5XX)

                with open(image_save_path, 'wb') as file:
                        file.write(response.content)
        return image_save_path
    except requests.HTTPError as e:
        # Specific handling for HTTP errors (e.g., 401, 403, 404)
        logging.error(f"HTTP Error for URL {url}: {e.response.status_code} {e.response.reason}")
        return None
    except requests.RequestException as e:
        # General request exceptions (e.g., connection errors)
        logging.error(f"Request Error for URL {url}: {str(e)}")
        return None
    except Exception as e:
        # Broad catch for unexpected errors (e.g., IO errors)
        logging.error(f"General Error for URL {url}: {str(e)}")
        return None


def _formate_price_columns(row):
    try:
        pricing = json.loads(row['QUANTITY_BREAK_PRICING'])
        # add quantity
        res = {}
        for type in ["Decorated", "Blank"]:
            # quantity
            if type in pricing and 'usd' in pricing[type] and pricing[type]['usd'] and 'qty' in pricing[type]['usd'] and pricing[type]['usd']['qty']:
                for i in range(1, 6):
                    res[f"{type}_q{i}"] = pricing[type]['usd']['qty'][i-1] if i-1 < len(pricing[type]['usd']['qty']) else 'N/A'
            else:
                for i in range(1, 6):
                    res[f"{type}_q{i}"] = 'N/A'

            # mc
            if type in pricing and 'usd' in pricing[type] and pricing[type]['usd'] and 'markup_code' in pricing[type]['usd'] and pricing[type]['usd']['markup_code']:
                res[f"{type}_mc_us"] = pricing[type]['usd']['markup_code']
            else:
                res[f"{type}_mc_us"] = '-'
            if type in pricing and 'cad' in pricing[type] and pricing[type]['cad'] and 'markup_code' in pricing[type]['usd'] and pricing[type]['usd']['markup_code']:
                res[f"{type}_mc_ca"] = pricing[type]['usd']['markup_code']
            else:
                res[f"{type}_mc_ca"] = '-'
                
            # usd price
            if type in pricing and 'usd' in pricing[type] and pricing[type]['usd'] and 'price_array' in pricing[type]['usd'] and pricing[type]['usd']['price_array']:
                for i in range(1, 6):
                    res[f"{type}_p_us_{i}"] = pricing[type]['usd']['price_array'][i-1] if i-1 < len(pricing[type]['usd']['price_array']) else 'N/A'
            else:
                for i in range(1, 6):
                    res[f"{type}_p_us_{i}"] = 'N/A'
                        
            # cad price
            if type in pricing and 'cad' in pricing[type] and pricing[type]['cad'] and 'price_array' in pricing[type]['cad'] and pricing[type]['cad']['price_array']:
                for i in range(1, 6):
                    res[f"{type}_p_ca_{i}"] = pricing[type]['cad']['price_array'][i-1] if i-1 < len(pricing[type]['cad']['price_array']) else 'N/A'
            else:
                for i in range(1, 6):
                    res[f"{type}_p_ca_{i}"] = 'N/A'
        return res
    except Exception as e:
        res = {}
        for type in ["Decorated", "Blank"]:
            for i in range(1, 6):
                res[f"{type}_q{i}"] = 'N/A'
                
            res[f"{type}_mc_us"] = '-'
            res[f"{type}_mc_ca"] = '-'

            for i in range(1, 6):
                res[f"{type}_p_us_{i}"] = 'N/A'
            for i in range(1, 6):
                res[f"{type}_p_ca_{i}"] = 'N/A'
        return res