"""Query analysis for intent detection and query expansion."""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class QueryIntent(Enum):
    """Types of query intents."""

    # "What is X?" / "Describe X" - Direct lookup
    DEFINITION = "definition"

    # "How does X work?" / "Explain X" - Need X + dependencies
    EXPLANATION = "explanation"

    # "List all X" / "How many X" - Aggregation query
    LIST_COUNT = "list_count"

    # "Where is X used?" / "What calls X?" - Reference search
    USAGE = "usage"

    # "Find X" / "Search for X" - General search
    SEARCH = "search"

    # "Compare X and Y" / "Difference between X and Y"
    COMPARISON = "comparison"

    # Schema/database related queries
    SCHEMA = "schema"


@dataclass
class QueryAnalysis:
    """Result of analyzing a query."""

    intent: QueryIntent
    primary_terms: list[str]  # Main terms to search for
    expanded_terms: list[str]  # Expanded/related terms
    class_names: list[str]  # Detected class names
    method_names: list[str]  # Detected method names
    suggested_top_k: int  # Recommended number of results
    min_similarity: float  # Recommended similarity threshold
    include_dependencies: bool  # Whether to fetch dependencies
    chunk_type_filter: Optional[str]  # Suggested chunk type filter


# Common programming term expansions
TERM_EXPANSIONS = {
    # Authentication/Security
    "auth": [
        "authentication",
        "authorize",
        "login",
        "credential",
        "token",
        "session",
        "security",
    ],
    "authentication": ["auth", "login", "credential", "token", "session", "security"],
    "login": ["auth", "authentication", "signin", "credential", "session"],
    "security": ["auth", "authentication", "permission", "role", "access", "token"],
    # Data operations
    "save": ["persist", "store", "write", "insert", "create", "update"],
    "load": ["read", "fetch", "get", "retrieve", "query"],
    "delete": ["remove", "destroy", "drop", "clear"],
    "update": ["modify", "change", "edit", "patch", "save"],
    # API/HTTP
    "api": ["endpoint", "rest", "controller", "route", "handler"],
    "request": ["http", "call", "invoke", "fetch"],
    "response": ["result", "return", "output"],
    # Database
    "database": ["db", "repository", "dao", "store", "persistence"],
    "query": ["select", "find", "search", "filter"],
    "table": ["entity", "model", "schema", "record"],
    # Error handling
    "error": ["exception", "failure", "fault", "issue"],
    "exception": ["error", "throw", "catch", "handle"],
    "validation": ["validate", "check", "verify", "sanitize"],
    # Common patterns
    "config": ["configuration", "settings", "properties", "options"],
    "util": ["utility", "helper", "common", "shared"],
    "service": ["manager", "handler", "processor", "provider"],
    "factory": ["builder", "creator", "generator"],
    # Payment/Transaction
    "payment": ["pay", "transaction", "checkout", "billing", "charge", "invoice"],
    "transaction": ["payment", "transfer", "operation"],
    # User/Account
    "user": ["account", "profile", "member", "customer"],
    "account": ["user", "profile", "credential"],
}


def analyze_query(question: str) -> QueryAnalysis:
    """Analyze a query to determine intent and extract key information.

    Args:
        question: The user's question

    Returns:
        QueryAnalysis with intent, terms, and recommendations
    """
    question_lower = question.lower().strip()

    # Extract potential class names (PascalCase)
    # Exclude common words and single letters
    common_words = {
        "I", "A", "The", "How", "What", "When", "Where", "Why", "Which", "Who",
        "This", "That", "These", "Those", "It", "Is", "Are", "Was", "Were",
        "Has", "Have", "Had", "Do", "Does", "Did", "Will", "Would", "Should",
        "Can", "Could", "May", "Might", "Must", "Shall", "To", "From", "For",
        "With", "Without", "By", "In", "On", "At", "Of", "And", "Or", "But",
    }
    
    raw_class_names = re.findall(
        r"\b([A-Z][a-zA-Z0-9]*(?:Bean|Facade|Record|Data|Config|Type|Service|"
        r"Manager|Handler|Controller|Utils|Helper|Factory|Builder|Parser|"
        r"Writer|Reader|Exception|Error|Interface|Abstract|Repository|Dao|"
        r"Entity|Model|Dto|Request|Response)?)\b",
        question,
    )
    
    # Filter out common words and single letters, require at least 2 characters
    class_names = [
        name for name in raw_class_names
        if len(name) >= 2 and name not in common_words
    ]

    # Extract potential method names (camelCase starting with lowercase)
    method_names = re.findall(
        r"\b([a-z][a-zA-Z0-9]*(?:get|set|is|has|can|do|make|create|build|"
        r"find|search|load|save|delete|update|process|handle|validate)?[A-Z][a-zA-Z0-9]*)\b",
        question,
    )

    # Detect intent
    intent = _detect_intent(question_lower)

    # Extract primary search terms
    primary_terms = _extract_primary_terms(question_lower, class_names, method_names)

    # Expand terms
    expanded_terms = _expand_terms(primary_terms)

    # Determine recommendations based on intent
    suggested_top_k, min_similarity, include_deps, chunk_type = _get_recommendations(
        intent, class_names, method_names
    )

    return QueryAnalysis(
        intent=intent,
        primary_terms=primary_terms,
        expanded_terms=expanded_terms,
        class_names=class_names,
        method_names=method_names,
        suggested_top_k=suggested_top_k,
        min_similarity=min_similarity,
        include_dependencies=include_deps,
        chunk_type_filter=chunk_type,
    )


def _detect_intent(question_lower: str) -> QueryIntent:
    """Detect the intent of a query."""

    # List/count queries - be more specific to avoid false positives
    # "which class" (singular) = asking for specific recommendation, NOT a list
    # "which classes" (plural) = asking for a list
    list_patterns = [
        "list all",
        "list the",
        "show all",
        "what are all",
        "what are the",
        "which classes",  # plural - this is a list query
        "which methods",  # plural
        "which files",    # plural
        "which ones",     # plural
        "which all",
        "how many",
        "count",
        "enumerate",
        "all the",
        "all indexed",
        "all classes",
        "all methods",
    ]
    if any(p in question_lower for p in list_patterns):
        return QueryIntent.LIST_COUNT
    
    # "which" + singular noun = asking for specific recommendation (definition/explanation)
    # Don't treat as list - let it fall through to other intent detection

    # Schema queries
    schema_patterns = [
        "schema",
        "database schema",
        "table",
        "ddl",
        "sql schema",
        "entity",
        "orm",
        "jpa",
        "hibernate",
        "model",
        "fields",
    ]
    if any(p in question_lower for p in schema_patterns):
        return QueryIntent.SCHEMA

    # Usage queries
    usage_patterns = [
        "where is",
        "who uses",
        "what uses",
        "what calls",
        "called by",
        "used by",
        "references to",
        "usages of",
        "find usages",
    ]
    if any(p in question_lower for p in usage_patterns):
        return QueryIntent.USAGE

    # Comparison queries
    comparison_patterns = [
        "compare",
        "difference between",
        "vs",
        "versus",
        "differ",
        "similar to",
        "different from",
    ]
    if any(p in question_lower for p in comparison_patterns):
        return QueryIntent.COMPARISON

    # Definition queries (direct lookup)
    definition_patterns = [
        "what is",
        "what's",
        "define",
        "describe",
        "tell me about",
        "show me",
        "get me",
    ]
    if any(p in question_lower for p in definition_patterns):
        return QueryIntent.DEFINITION

    # Explanation queries (need context)
    explanation_patterns = [
        "how does",
        "how do",
        "explain",
        "why does",
        "why do",
        "how is",
        "how are",
        "what happens when",
        "walk through",
        "which class will",
        "which method will",
        "which should",
        "which would",
        "which can",
    ]
    if any(p in question_lower for p in explanation_patterns):
        return QueryIntent.EXPLANATION

    # Default to search
    return QueryIntent.SEARCH


def _extract_primary_terms(
    question_lower: str, class_names: list[str], method_names: list[str]
) -> list[str]:
    """Extract primary search terms from the question."""

    # Start with class and method names
    terms = list(class_names) + list(method_names)

    # Remove common stop words and question words
    stop_words = {
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "must",
        "shall",
        "can",
        "need",
        "dare",
        "ought",
        "used",
        "to",
        "of",
        "in",
        "for",
        "on",
        "with",
        "at",
        "by",
        "from",
        "as",
        "into",
        "through",
        "during",
        "before",
        "after",
        "above",
        "below",
        "between",
        "under",
        "again",
        "further",
        "then",
        "once",
        "what",
        "which",
        "who",
        "whom",
        "this",
        "that",
        "these",
        "those",
        "am",
        "it",
        "its",
        "it's",
        "and",
        "but",
        "if",
        "or",
        "because",
        "as",
        "until",
        "while",
        "how",
        "where",
        "when",
        "why",
        "all",
        "each",
        "every",
        "both",
        "few",
        "more",
        "most",
        "other",
        "some",
        "such",
        "no",
        "nor",
        "not",
        "only",
        "own",
        "same",
        "so",
        "than",
        "too",
        "very",
        "just",
        "also",
        "now",
        "here",
        "there",
        "me",
        "my",
        "i",
        "you",
        "your",
        "we",
        "our",
        "they",
        "their",
        "show",
        "tell",
        "get",
        "find",
        "search",
        "look",
        "describe",
        "explain",
        "list",
    }

    # Extract words from question
    words = re.findall(r"\b[a-z][a-z0-9_]*\b", question_lower)

    for word in words:
        if (
            word not in stop_words
            and len(word) > 2
            and word not in [t.lower() for t in terms]
        ):
            terms.append(word)

    return terms[:10]  # Limit to 10 primary terms


def _expand_terms(primary_terms: list[str]) -> list[str]:
    """Expand primary terms with related terms."""

    expanded = set()

    for term in primary_terms:
        term_lower = term.lower()

        # Check direct expansions
        if term_lower in TERM_EXPANSIONS:
            expanded.update(TERM_EXPANSIONS[term_lower])

        # Check if term is part of any expansion key
        for key, expansions in TERM_EXPANSIONS.items():
            if term_lower in expansions:
                expanded.add(key)
                expanded.update(expansions)

    # Remove terms already in primary
    primary_lower = {t.lower() for t in primary_terms}
    expanded = [t for t in expanded if t.lower() not in primary_lower]

    return expanded[:15]  # Limit expanded terms


def _get_recommendations(
    intent: QueryIntent, class_names: list[str], method_names: list[str]
) -> tuple[int, float, bool, Optional[str]]:
    """Get recommendations based on intent.

    Returns:
        (suggested_top_k, min_similarity, include_dependencies, chunk_type_filter)
    """

    if intent == QueryIntent.DEFINITION:
        # Direct lookup - fewer results, high threshold
        return (5, 0.6, False, "class" if class_names else None)

    elif intent == QueryIntent.EXPLANATION:
        # Need more context and dependencies
        return (10, 0.5, True, None)

    elif intent == QueryIntent.LIST_COUNT:
        # Aggregation - many results, lower threshold
        return (50, 0.3, False, "class")

    elif intent == QueryIntent.USAGE:
        # Reference search - medium results
        return (15, 0.5, False, None)

    elif intent == QueryIntent.COMPARISON:
        # Need multiple items
        return (10, 0.5, False, None)

    elif intent == QueryIntent.SCHEMA:
        # Schema queries need full context
        return (10, 0.5, True, "class")

    else:  # SEARCH
        # Default search
        return (10, 0.5, False, None)


def get_keywords_for_search(analysis: QueryAnalysis) -> list[str]:
    """Get keywords for hybrid keyword search.

    Args:
        analysis: QueryAnalysis result

    Returns:
        List of keywords for keyword-based search
    """
    keywords = []

    # Add class and method names (highest priority)
    keywords.extend(analysis.class_names)
    keywords.extend(analysis.method_names)

    # Add primary terms
    keywords.extend(analysis.primary_terms)

    # Deduplicate while preserving order
    seen = set()
    unique_keywords = []
    for kw in keywords:
        kw_lower = kw.lower()
        if kw_lower not in seen:
            seen.add(kw_lower)
            unique_keywords.append(kw)

    return unique_keywords[:10]  # Limit to 10 keywords
