# Configuration for query processing, including vague word detection and query enhancement settings

# List of vague words/phrases that may indicate ambiguity in user questions
VAGUE_WORDS = [
    'it', 'that', 'this', 'these', 'those', 'they', 'their', 'them', 'the company', 'the deal', 'the investment', 'same', 'also', 'too'
]

# Patterns that indicate the user is asking about a metric without specifying the company
METRIC_ONLY_PATTERNS = [
    'revenue', 'valuation', 'profit', 'growth', 'ebitda', 'customers', 'users', 'employees'
]

# Query Enhancement Settings
QUERY_REWRITER_TEMPERATURE = 0.1 # No Major creativity, just clarity
QUERY_REWRITER_MAX_TOKENS  = 1500   # User questions can be up to 1000 words
