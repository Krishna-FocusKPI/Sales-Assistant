from dataclasses import dataclass


@dataclass
class News:
    date: str = None
    title: str = None
    url: str = None
    content: str = None
    summary: str = None


@dataclass
class ToNextMemory:
    message: str = None
    decision: str = None
    source: str = None
    data = None
    
    def reset(self):
        self.message = None
        self.decision = None
        self.source = None
        self.data = None


@dataclass
class WorkFlowMemory:    
    # step 1 - verify naics code
    distributor_id: str = None
    distributor_name: str = None
    distributor_used_name: list = None

    # step 2 - validate category
    logo_name: str = None
    has_recurring: bool = None
    logo_candidates = None
    
    # step 3 - recommendation
    category_recommendation: str = None
    category = None
    visited_categories = None
    
    # step 3 - recommendation
    recommendations = None
    all_available_products = None
    
    shopping_list = None
    filters = None
    filtered_products = None
    
    # step 4 - build deck
    logo_sales_analysis_date = None
    logo_sales_analysis = None
    
    yoy_analysis = None
    
    need_news_analysis: bool = False
    news_analysis: dict = None
    
    deck_name = None