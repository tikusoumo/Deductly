import os
import json
from typing import Any, Dict, List, TypedDict
import asyncio

from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import GoogleGenerativeAIEmbeddings, GoogleGenerativeAI
from langchain_qdrant import Qdrant
from qdrant_client.models import Filter, FieldCondition, MatchValue

# --- IMPORT TAX CALCULATOR ---
from tax_deductions import TaxCalculator # Relative import

# ─── INITIAL SETUP ────────────────────────────────────────────────────────────
# Explicitly define the path to the .env file within the rag_pipeline directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOTENV_PATH = os.path.join(BASE_DIR, '.env')
# load_dotenv(dotenv_path=DOTENV_PATH, override=True)
load_dotenv()

# ─── CONFIGURATION ────────────────────────────────────────────────────────────
# These variables should now be loaded correctly from .env
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Essential check after loading env vars
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable not set. Check your .env file.")
if not QDRANT_URL:
    raise ValueError("QDRANT_URL environment variable not set. Check your .env file.")
if not QDRANT_API_KEY:
    raise ValueError("QDRANT_API_KEY environment variable not set. Check your .env file.")

os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY # Ensure it's in os.environ for some langchain modules
os.environ["QDRANT_API_KEY"] = QDRANT_API_KEY # Ensure it's in os.environ for qdrant-client

EMBEDDING_MODEL = "models/text-embedding-004"
LLM_MODEL = "gemini-2.0-flash"
llm = GoogleGenerativeAI(model=LLM_MODEL) # This LLM instance is used by plan_chain and reason_chain

COLLECTIONS = [
    "tax_law_chunks",
    "tax_rules_chunks",
    "capital_gain_cases",
    "cbdt_notifications",
    "itr_forms",
]

# ─── STATE ────────────────────────────────────────────────────────────────────
class TaxState(TypedDict, total=False):
    user_details: dict
    deduction_plan: dict
    eligible_deductions: dict
    missing_data_questions: dict
    rag_results: dict
    reasoning: dict
    summary: str
    legal_basis: str
    verdict: str
    analyzed_query: dict # New field to store analyzed queries
    total_deductions: float # New field
    total_taxable_income: float # New field
    tax_liability: float # New field

# ─── SET UP LLM CHAINS (Modernized with LCEL) ─────────────────────────────────
plan_prompt = PromptTemplate(
    input_variables=["user_details"],
    template="""
You are a tax assistant. Given these user details (JSON):
{user_details}

Identify ALL potential tax deductions applicable under Indian Income Tax law for a salaried individual (FY 2024-25, AY 2025-26).
For each potential deduction, return a JSON object where the key is the deduction name (use these exact keys: "standard_deduction", "section_80C_deduction", "section_80D_deduction", "section_24B_deduction", "section_80G_deduction", "section_80CCD1B_deduction", "section_80E_deduction", "section_80DD_deduction", "section_80TTA_deduction", "section_80TTB_deduction").
For each deduction, the value should be an object with:
- eligibility_criteria: a short description of the general eligibility.
- required_fields: a list of specific fields from user_details (e.g., 'salary', 'health_insurance_premium', 'donation_amount', 'housing_loan_interest', 'investments.80C_investments', 'investments.nps_contribution', 'education_loan_interest', 'disability_details.is_disabled', 'disability_details.type', 'other_income.interest_from_savings', 'age_self', 'age_parents', 'property_status') that are crucial for determining eligibility and calculating the amount. Use dot notation for nested fields.
- query: a short free-text query to fetch relevant legal context for that specific deduction.

Be comprehensive and list all basic deductions, even if the user_details currently lack the required fields.
For example, if user_details does not contain 'investments.nps_contribution', you should still include "section_80CCD1B_deduction" but specify 'investments.nps_contribution' as a 'required_field'.

Respond with ONLY the JSON object.
""".strip(),
)
plan_chain = plan_prompt | llm | JsonOutputParser()

# New: Query Analyzer Chain
query_analyzer_prompt = PromptTemplate(
    input_variables=["query"],
    template="""
Analyze the following tax deduction query and extract any explicit Indian Income Tax sections (e.g., "80C", "24B") or rules (e.g., "Rule 11DD").
Return the output as a JSON object with two keys: "sections" (list of strings) and "rules" (list of strings).
If no specific section or rule is mentioned, return empty lists.

Query: {query}

Example Output:
{{
    "sections": ["80C", "80D"],
    "rules": ["Rule 11DD"]
}}
""".strip(),
)
query_analyzer_chain = query_analyzer_prompt | llm | JsonOutputParser()

reason_prompt = PromptTemplate(
    input_variables=["user_facts", "deduction", "contexts"],
    template="""
You are a tax reasoning assistant.
Deduction: {deduction}
User facts (JSON): {user_facts}
Legal contexts (separated by ----):
{contexts}

If a specific Python function in `TaxCalculator` for this deduction is available and already calculates the amount, just confirm that the calculation is handled externally.
Otherwise, use the provided legal contexts and user facts to produce a JSON with:
- amount: computed deductible amount or range as a string (e.g., "Up to ₹1,50,000")
- summary: concise explanation of why, referencing the legal context if used.
- citations: list of section/rule/case IDs used.

Respond with ONLY the JSON object.
""".strip(),
)
reason_chain = reason_prompt | llm | JsonOutputParser()

# ─── BUILD MULTI-COLLECTION RETRIEVER (Async Version) ──────────────────────────
embedder = GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL)

# Initialize Qdrant clients with async capability
retrievers = {
    name: Qdrant.from_existing_collection(
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY,
        collection_name=name,
        embedding=embedder,
    )
    for name in COLLECTIONS
}

def get_nested_field(data: dict, field_path: str):
    """Helper to get a nested field using dot notation."""
    parts = field_path.split('.')
    current = data
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None # Field not found at this level
    return current

def plan_node(state: TaxState) -> dict:
    """Generate a list of applicable deductions based on user input."""
    print("--- Executing Node: Plan ---")
    user_details = state["user_details"]
    response = plan_chain.invoke({"user_details": json.dumps(user_details)})
    return {"deduction_plan": response}

def filter_node(state: TaxState) -> dict:
    """Check which deductions the user is eligible for based on available data."""
    print("--- Executing Node: Filter ---")
    user_details = state["user_details"]
    deduction_plan = state["deduction_plan"]
    eligible = {}
    for k, v in deduction_plan.items():
        all_fields_present = True
        for field in v.get("required_fields", []):
            if get_nested_field(user_details, field) is None:
                all_fields_present = False
                break
        
        if all_fields_present:
            eligible[k] = v
    return {"eligible_deductions": eligible}

def clarify_node(state: TaxState) -> dict:
    """Detect missing fields by checking the original plan."""
    print("--- Executing Node: Clarify ---")
    user_details = state["user_details"]
    deduction_plan = state["deduction_plan"]
    missing = {}
    for name, info in deduction_plan.items():
        missing_fields = []
        for field in info.get("required_fields", []):
            if get_nested_field(user_details, field) is None:
                missing_fields.append(field)
        
        if missing_fields:
            missing[name] = missing_fields
    return {"missing_data_questions": missing}

async def analyze_query_node(state: TaxState) -> dict:
    """Analyzes each deduction query to extract structured search parameters."""
    print("--- Executing Node: Analyze Query ---")
    deduction_plan = state["deduction_plan"]
    analyzed_queries = {}
    
    analysis_tasks = []
    deduction_names = []

    for name, info in deduction_plan.items():
        query = info.get("query")
        if query:
            analysis_tasks.append(query_analyzer_chain.ainvoke({"query": query}))
            deduction_names.append(name)
        else:
            analyzed_queries[name] = {"sections": [], "rules": []}

    results_from_analysis = await asyncio.gather(*analysis_tasks)

    for i, name in enumerate(deduction_names):
        analyzed_queries[name] = results_from_analysis[i]
            
    return {"analyzed_query": analyzed_queries}

async def rag_node(state: TaxState) -> dict:
    """
    Performs a multi-stage, metadata-filtered retrieval for each deduction asynchronously.
    """
    print("--- Executing Node: RAG (Filtered Retrieval) ---")
    deduction_plan = state["deduction_plan"]
    analyzed_queries = state["analyzed_query"]
    rag_results = {}

    all_deduction_rag_tasks = []
    deduction_names_for_tasks = []

    for name, info in deduction_plan.items():
        original_query = info.get("query")
        if not original_query:
            rag_results[name] = []
            continue

        analysis = analyzed_queries.get(name, {"sections": [], "rules": []})
        sections = analysis.get("sections", [])
        rules = analysis.get("rules", [])

        current_deduction_tasks = []
        
        # Tier 1: Primary Sources (Laws and Rules) with strict filtering
        primary_filter = Filter(
            should=[
                FieldCondition(key="metadata.section", match=MatchValue(value=s)) for s in sections
            ] + [
                FieldCondition(key="metadata.rule", match=MatchValue(value=r)) for r in rules
            ]
        )

        if sections or rules:
            # CORRECTED: Changed 'query_filter=' to 'filter='
            current_deduction_tasks.append(retrievers["tax_law_chunks"].asimilarity_search_with_score(query=original_query, k=3, filter=primary_filter))
            current_deduction_tasks.append(retrievers["tax_rules_chunks"].asimilarity_search_with_score(query=original_query, k=3, filter=primary_filter))
            
        # Always do a broad semantic search as a fallback or for general queries (async)
        current_deduction_tasks.append(retrievers["tax_law_chunks"].asimilarity_search_with_score(query=original_query, k=2))
        current_deduction_tasks.append(retrievers["tax_rules_chunks"].asimilarity_search_with_score(query=original_query, k=2))

        # Tier 2 & 3: Supporting Documents (Notifications, Cases) (async)
        if sections: # Only apply section filter if sections are identified
            case_filter = Filter(
                should=[FieldCondition(key="metadata.section", match=MatchValue(value=s)) for s in sections]
            )
            # CORRECTED: Changed 'query_filter=' to 'filter='
            current_deduction_tasks.append(retrievers["capital_gain_cases"].asimilarity_search_with_score(query=original_query, k=2, filter=case_filter))
            current_deduction_tasks.append(retrievers["cbdt_notifications"].asimilarity_search_with_score(query=original_query, k=2, filter=case_filter))
        else: # If no sections, do a broad search on supporting documents
              current_deduction_tasks.append(retrievers["capital_gain_cases"].asimilarity_search_with_score(query=original_query, k=2))
              current_deduction_tasks.append(retrievers["cbdt_notifications"].asimilarity_search_with_score(query=original_query, k=2))

        all_deduction_rag_tasks.append(asyncio.gather(*current_deduction_tasks))
        deduction_names_for_tasks.append(name)

    # Execute all tasks for all deductions in parallel
    results_for_all_deductions = await asyncio.gather(*all_deduction_rag_tasks)

    for i, name in enumerate(deduction_names_for_tasks):
        all_retrieved_chunks_for_deduction = {}
        for hits_list in results_for_all_deductions[i]:
            for chunk, score in hits_list:
                all_retrieved_chunks_for_deduction[chunk.page_content] = chunk # Deduplicate by content
        
        rag_results[name] = [chunk.page_content for chunk in all_retrieved_chunks_for_deduction.values()]

    return {"rag_results": rag_results}


def reason_node(state: TaxState) -> dict:
    """
    Reason whether the deduction applies, using specific calculation functions
    from TaxCalculator if available, otherwise falling back to LLM reasoning.
    Includes all planned deductions, marking those with missing data as N/A.
    """
    print("--- Executing Node: Reason ---")
    user_details = state["user_details"]
    deduction_plan = state["deduction_plan"]
    rag_results = state["rag_results"]
    reasoning = {}

    # Instantiate your TaxCalculator with the user's details
    calculator = TaxCalculator(user_details)

    for name, plan_info in deduction_plan.items():
        result = {}
        
        # Check if all required fields are present for this specific deduction
        all_fields_present = True
        for field in plan_info.get("required_fields", []):
            if get_nested_field(user_details, field) is None:
                all_fields_present = False
                break

        if not all_fields_present:
            # If data is missing, mark as N/A and provide specific questions
            missing_fields_list = state["missing_data_questions"].get(name, [])
            
            result = {
                "amount": "N/A",
                "summary": f"Data missing for this deduction. Please provide: {', '.join(missing_fields_list) if missing_fields_list else 'required information'}.",
                "citations": [plan_info.get("eligibility_criteria", "N/A")]
            }
            reasoning[name] = result
            continue

        # --- Dispatch to specific calculation functions if all data is present ---
        if name == "standard_deduction":
            tax_regime_choice = user_details.get("tax_regime", "old")
            result = calculator.calculate_standard_deduction(tax_regime=tax_regime_choice)
        elif name == "section_80C_deduction":
            result = calculator.calculate_section_80C_deduction()
        elif name == "section_80D_deduction":
            result = calculator.calculate_section_80D_deduction()
        elif name == "section_24B_deduction":
            result = calculator.calculate_section_24B_deduction()
        elif name == "section_80G_deduction":
            result = calculator.calculate_section_80G_deduction()
        elif name == "section_80CCD1B_deduction":
            result = calculator.calculate_section_80CCD1B_deduction()
        elif name == "section_80E_deduction":
            result = calculator.calculate_section_80E_deduction()
        elif name == "section_80DD_deduction":
            result = calculator.calculate_section_80DD_deduction()
        elif name == "section_80TTA_deduction":
            result = calculator.calculate_section_80TTA_deduction()
        elif name == "section_80TTB_deduction":
            result = calculator.calculate_section_80TTB_deduction()
        else:
            # Fallback to LLM for non-calculator deductions or complex cases
            print(f"LLM reasoning for: {name} (no specific function or for augmentation)")
            contexts = "\n----\n".join(rag_results.get(name, []))
            resp = reason_chain.invoke(
                {
                    "deduction": name,
                    "user_facts": json.dumps(user_details),
                    "contexts": contexts,
                }
            )
            if isinstance(resp, str):
                try:
                    result = json.loads(resp)
                except json.JSONDecodeError:
                    result = {"amount": "Error", "summary": f"Could not parse LLM response for {name}: {resp}", "citations": []}
            else:
                result = resp

        if result:
            reasoning[name] = result
        else:
            reasoning[name] = {"amount": "N/A", "summary": "Could not determine deduction.", "citations": []}

    return {"reasoning": reasoning}

def calculate_totals_node(state: TaxState) -> dict:
    """Calculate total deductions, total taxable income, and tax liability."""
    print("--- Executing Node: Calculate Totals ---")
    user_details = state["user_details"]
    reasoning = state["reasoning"]

    calculator = TaxCalculator(user_details) # Re-instantiate calculator with user details

    total_deductions = 0.0
    for deduction_name, deduction_info in reasoning.items():
        amount_str = deduction_info.get("amount", "N/A")
        # Try to extract a numeric value from the amount string
        if isinstance(amount_str, (int, float)):
            amount = float(amount_str)
        elif isinstance(amount_str, str):
            # Extract numbers from string, e.g., "Up to ₹1,50,000" -> 150000
            import re
            numbers = re.findall(r'\d+', amount_str.replace(',', ''))
            if numbers:
                amount = float(numbers[0]) # Take the first number found
            else:
                amount = 0.0 # If no number found, consider it 0 for total
        else:
            amount = 0.0
        
        # Ensure we only add valid numeric deductions
        if amount_str != "N/A" and amount > 0:
            total_deductions += amount

    # Calculate Total Taxable Income
    # Assuming 'salary' is the primary income, and other_income are additions
    # This part needs to be robust based on your TaxCalculator's capabilities
    # You might want to have a get_gross_income method in TaxCalculator
    gross_income = user_details.get("salary", 0) + user_details.get("other_income", {}).get("fixed_deposit_interest", 0) + user_details.get("other_income", {}).get("interest_from_savings", 0)

    # Note: If your TaxCalculator has a more comprehensive way to get gross income, use it.
    # For instance: gross_income = calculator.calculate_gross_income()

    total_taxable_income = gross_income - total_deductions
    if total_taxable_income < 0:
        total_taxable_income = 0 # Taxable income cannot be negative

    # Calculate Tax Liability
    # This heavily depends on your TaxCalculator's implementation
    tax_liability = calculator.calculate_tax_liability(total_taxable_income)


    return {
        "total_deductions": total_deductions,
        "total_taxable_income": total_taxable_income,
        "tax_liability": tax_liability
    }


def summary_node(state: TaxState) -> dict:
    """Summarize all deductions and amounts."""
    print("--- Executing Node: Summary ---")
    reasoning = state["reasoning"]
    lines = []
    for k in sorted(reasoning.keys()):
        v = reasoning[k]
        lines.append(f"- **{k}**: {v.get('amount', 'N/A')} ({v.get('summary', 'No summary available')})")
    return {"summary": "\n".join(lines)}

def legal_node(state: TaxState) -> dict:
    """Summarize the legal basis (sections/cases) for deductions."""
    print("--- Executing Node: Legal ---")
    reasoning = state["reasoning"]
    lines = []
    for k in sorted(reasoning.keys()):
        v = reasoning[k]
        citations = v.get('citations', [])
        if v.get('amount', 'N/A') == 'N/A' and citations:
             lines.append(f"- **{k}**: Eligibility criteria: {', '.join(citations)}")
        elif citations:
            lines.append(f"- **{k}**: {', '.join(citations)}")
        else:
            lines.append(f"- **{k}**: No specific citations available.")
    return {"legal_basis": "\n".join(lines)}

def verdict_node(state: TaxState) -> dict:
    """Compile final deduction verdict."""
    print("--- Executing Node: Verdict ---")
    summary = state["summary"]
    legal_basis = state["legal_basis"]
    total_deductions = state.get("total_deductions", 0.0)
    total_taxable_income = state.get("total_taxable_income", 0.0)
    tax_liability = state.get("tax_liability", 0.0)

    verdict = "\n".join(
        [
            "## Deduction Summary",
            summary,
            "",
            f"**Total Estimated Deductions**: ₹{total_deductions:,.2f}",
            f"**Total Estimated Taxable Income**: ₹{total_taxable_income:,.2f}",
            f"**Total Estimated Tax Liability**: ₹{tax_liability:,.2f}",
            "",
            "## Legal Basis",
            legal_basis,
            "",
            "⚖️ This summary is based on the provided facts and Indian IT laws. Please consult a tax professional for personalized advice."
        ]
    )
    return {"verdict": verdict}

# ─── GRAPH DEFINITION ────────────────────────────────────────────────────────
graph_builder = StateGraph(TaxState)

# Add all the functions as standard nodes
graph_builder.add_node("plan_node", plan_node)
graph_builder.add_node("filter_node", filter_node)
graph_builder.add_node("clarify_node", clarify_node)
graph_builder.add_node("analyze_query_node", analyze_query_node) # New node
graph_builder.add_node("rag_node", rag_node)
graph_builder.add_node("reason_node", reason_node)
graph_builder.add_node("calculate_totals_node", calculate_totals_node) # New node
graph_builder.add_node("summary_node", summary_node)
graph_builder.add_node("legal_node", legal_node)
graph_builder.add_node("verdict_node", verdict_node)

# Set the entry point and define the graph's sequential flow
graph_builder.set_entry_point("plan_node")
graph_builder.add_edge("plan_node", "filter_node") 
graph_builder.add_edge("filter_node", "clarify_node")
graph_builder.add_edge("clarify_node", "analyze_query_node") # New edge
graph_builder.add_edge("analyze_query_node", "rag_node") # Changed edge
graph_builder.add_edge("rag_node", "reason_node")
graph_builder.add_edge("reason_node", "calculate_totals_node") # New edge
graph_builder.add_edge("calculate_totals_node", "summary_node") # New edge
graph_builder.add_edge("summary_node", "legal_node")
graph_builder.add_edge("legal_node", "verdict_node")
graph_builder.add_edge("verdict_node", END)

# Compile the graph
graph = graph_builder.compile()

# ─── DEMO RUN ──────────────────────────────────────────────────────────────────
# This block is for direct testing of the graph, not for import by app.py
# In app.py, graph is imported directly.
if __name__ == "__main__":
    initial_state = {
        
    "user_details": {
        "salary": 1200000,
        "user_age": 35,
        "is_senior_citizen": "false",
        "health_insurance_premium": 25000,
        "parents_age": 62,
        "parents_health_insurance_premium": 40000,
        "medical_expenses": 12000,
        "donation_amount": 30000,
        "housing_loan_interest": 180000,
        "investments": {
          "80C_investments": 140000,
          "nps_contribution": 50000
        },
        "education_loan_interest": 40000,
        "other_income": {
          "interest_from_savings": 8000,
          "fixed_deposit_interest": 20000
        },
        "property_status": "self_occupied"
    }

    }
    
    print("🚀 Invoking the tax graph...")
    # Changed to ainvoke for consistency with FastAPI
    final_result = asyncio.run(graph.ainvoke(initial_state))

    print("\n\n✅ Final Verdict:\n")
    print(final_result.get("verdict", "No verdict could be generated."))