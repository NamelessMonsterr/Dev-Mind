"""
Prompt templates for DevMind LLM interactions.
"""

from typing import List, Dict

# System prompts
SYSTEM_PROMPT_BASE = """You are DevMind, an intelligent code assistant with access to a semantic codebase search system.

Your capabilities:
- Semantic code search across the entire codebase
- Understanding code structure and relationships
- Explaining code functionality
- Debugging assistance
- Architecture analysis

CRITICAL RULES:
1. ONLY use information from the provided context
2. If context doesn't contain the answer, say so explicitly
3. Always cite file paths and line numbers when referencing code
4. Do not hallucinate or make up information
5. Be concise but thorough"""

# Chat mode prompt
CHAT_PROMPT_TEMPLATE = """<context>
{context}
</context>

User Question: {query}

Based ONLY on the context provided above, answer the user's question. Include file paths and line numbers in your answer.

If the context doesn't contain relevant information, say: "I don't have enough information in the codebase to answer this question."

Answer:"""

# Code explanation prompt
CODE_EXPLANATION_PROMPT = """<context>
{context}
</context>

Explain the following code:

File: {file_path}
Lines: {start_line}-{end_line}

Provide:
1. High-level purpose
2. Key functionality
3. Dependencies and relationships
4. Important implementation details

Explanation:"""

# Multi-file reasoning prompt
MULTI_FILE_REASONING_PROMPT = """<context>
{context}
</context>

Analyze the interaction between these code sections:

Question: {query}

Provide:
1. How these components interact
2. Data flow between them
3. Key dependencies
4. Potential issues or concerns

Analysis:"""

# Architecture explanation prompt
ARCHITECTURE_PROMPT = """<context>
{context}
</context>

Based on the codebase context above, explain the architecture:

Focus area: {query}

Provide:
1. **Components**: List main components/modules
2. **Relationships**: How they interact
3. **Data Flow**: Key data flows
4. **Design Patterns**: Notable patterns used

Architecture Overview:"""

# Debugging assistance prompt
DEBUG_PROMPT = """<context>
{context}
</context>

Debug assistance needed:

Issue: {query}

Based on the code context, provide:
1. **Likely Cause**: Most probable causes
2. **Evidence**: Specific code that supports your analysis
3. **Solution**: Recommended fix with code examples
4. **Prevention**: How to prevent similar issues

Debugging Analysis:"""

# Code rewrite suggestion prompt
REWRITE_SUGGESTION_PROMPT = """<context>
{context}
</context>

Original Code:
```
{code}
```

Improvement Goal: {query}

Provide:
1. **Analysis**: Issues in current code
2. **Improved Version**: Rewritten code
3. **Explanation**: Why the changes improve it
4. **Trade-offs**: Any considerations

Rewrite Suggestion:"""

# Query expansion prompt
QUERY_EXPANSION_PROMPT = """Given the following query about code:

"{query}"

Generate 3-5 alternative phrasings or related queries that would help find relevant code.
Focus on:
- Synonyms for programming concepts
- Related technical terms
- Different ways developers might implement this

Format as JSON list:
```json
["query1", "query2", "query3"]
```

Expanded queries:"""

# Reasoning chain prompt (R1-style)
REASONING_CHAIN_PROMPT = """Think step-by-step to answer this question:

Question: {query}

Available context:
{context}

Break down your reasoning:

<thinking>
1. What information do I need?
2. What does the context tell me?
3. Are there gaps in my understanding?
4. What conclusions can I draw?
</thinking>

<answer>
[Your final answer based on reasoning]
</answer>"""

# Summary prompt
SUMMARY_PROMPT = """Summarize the following code or documentation:

{content}

Provide a concise summary (2-3 sentences) covering:
- Main purpose
- Key functionality
- Important details

Summary:"""

# Citation extraction prompt
CITATION_EXTRACTION_PROMPT = """From the following answer, extract all file references:

Answer:
{answer}

Extract:
- File paths
- Line numbers (if mentioned)
- Section references

Format as JSON:
```json
[
  {{"file": "path/to/file.py", "lines": "10-20", "relevance": "description"}}
]
```

Citations:"""


def build_chat_prompt(query: str, context: str) -> str:
    """Build chat prompt."""
    return CHAT_PROMPT_TEMPLATE.format(query=query, context=context)


def build_code_explanation_prompt(
    context: str,
    file_path: str,
    start_line: int,
    end_line: int
) -> str:
    """Build code explanation prompt."""
    return CODE_EXPLANATION_PROMPT.format(
        context=context,
        file_path=file_path,
        start_line=start_line,
        end_line=end_line
    )


def build_architecture_prompt(query: str, context: str) -> str:
    """Build architecture analysis prompt."""
    return ARCHITECTURE_PROMPT.format(query=query, context=context)


def build_debug_prompt(query: str, context: str) -> str:
    """Build debugging prompt."""
    return DEBUG_PROMPT.format(query=query, context=context)


def build_reasoning_prompt(query: str, context: str) -> str:
    """Build reasoning chain prompt."""
    return REASONING_CHAIN_PROMPT.format(query=query, context=context)


def build_summary_prompt(content: str) -> str:
    """Build summary prompt."""
    return SUMMARY_PROMPT.format(content=content)
