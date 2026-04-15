from dataclasses import dataclass


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
    naics_code: str = None
    industry: str = None

    # step 2 - validate category
    category: str = None
    visited_categories = None

    # step 3 - recommendation
    recommendations = None
    all_available_products = None
    
    shopping_list = None
    filters = None
    filtered_products = None
    
    # step 4 - build deck
    deck_name = None
    deck_path: str = None