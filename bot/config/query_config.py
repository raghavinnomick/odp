# Configuration for query processing, including vague word detection and query enhancement settings

# List of patterns that may indicate a greeting or non-informative question
GREETING_PATTERNS = {
    "hello", "hi", "hey", "hiya", "howdy", "good morning", "good afternoon", "good evening", "good day", "how are you", "how r u", "what's up", "whats up", "sup", "thanks", "thank you", "thank you!", "thanks!", "cheers", "bye", "goodbye", "see you", "talk later", "ok", "okay", "alright", "got it", "noted", "yes", "no", "sure", "great", "perfect", "sounds good",
}

# Signals that indicate the LLM could not confirm some facts and is asking the user for missing info. Transaction-safe.
MISSING_INFO_SIGNALS = [
    "we don't have",
    "we do not have",
    "not in our knowledge base",
    "not found in our",
    "could you provide",
    "could you share",
    "please provide",
    "please share",
    "i need the following",
    "missing from our knowledge base",
    "not present in our documents",
    "i don't have",
    "i do not have",
]

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
