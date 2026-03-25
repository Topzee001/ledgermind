"""
Rule-based text categorization.
Functions as a fallback when AI is unavailable or as a quick first pass.
"""

EXPENSE_RULES = {
    'Food & Dining': ['restaurant', 'cafe', 'coffee', 'lunch', 'dinner', 'snack', 'mcdonalds', 'kfc', 'starbucks', 'dominos', 'burger king'],
    'Groceries': ['supermarket', 'grocery', 'walmart', 'tesco', 'aldi', 'spar', 'shoprite', 'farm', 'market', 'provisions'],
    'Transportation': ['uber', 'bolt', 'lyft', 'taxi', 'cab', 'transit', 'train', 'bus', 'flight', 'airline', 'fuel', 'gas station', 'nnpc', 'total', 'mobil'],
    'Utilities': ['electricity', 'water', 'gas', 'internet', 'broadband', 'mobile', 'airtime', 'data', 'mtn', 'airtel', 'glo', '9mobile', 'phed', 'ikedc', 'ekedc'],
    'Software & Subscriptions': ['netflix', 'spotify', 'aws', 'amazon web', 'google cloud', 'azure', 'github', 'zoom', 'slack', 'microsoft', 'adobe', 'canva', 'digitalocean'],
    'Office Supplies': ['stationery', 'paper', 'ink', 'printer', 'desk', 'chair', 'office', 'staples'],
    'Marketing': ['facebook ads', 'google ads', 'instagram', 'twitter', 'linkedin ads', 'billboard', 'advert'],
    'Rent': ['rent', 'lease', 'landlord', 'property'],
    'Payroll': ['salary', 'wages', 'compensation', 'stipend', 'allowance', 'bonus'],
    'Consulting & Legal': ['consultant', 'lawyer', 'legal', 'accounting', 'audit', 'tax'],
    'Bank Charges': ['transfer fee', 'card maintenance', 'sms alert', 'stamp duty', 'account fee'],
}

INCOME_RULES = {
    'Sales Revenue': ['stripe', 'paypal', 'pos', 'interswitch', 'paystack', 'flutterwave', 'customer', 'sale'],
    'Investment Income': ['dividend', 'interest', 'capital gain', 'roi'],
    'Loan': ['loan', 'credit', 'advance', 'overdraft'],
    'Refunds': ['refund', 'reversal', 'returned'],
    'Freelance/Contract': ['upwork', 'fiverr', 'toptal', 'contract', 'freelance'],
}

def apply_rule_based_categorization(description, transaction_type='expense'):
    """
    Apply simple keyword matching to find a category.
    """
    if not description:
        return 'Other'

    desc_lower = description.lower()
    
    rules = EXPENSE_RULES if transaction_type.lower() == 'expense' else INCOME_RULES
    
    for category_name, keywords in rules.items():
        if any(keyword in desc_lower for keyword in keywords):
            return category_name
            
    return 'Other'
