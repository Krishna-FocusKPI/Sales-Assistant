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
    distributor_id: str = None
    distributor_name: str = None
    distributor_used_name: list = None
    
    # step 3 - recommendation
    category = None
    visited_categories = None
    
    # step 3 - recommendation
    recommendations = None
    all_available_products = None
    
    shopping_list = None
    filters = None
    filtered_products = None
