# main_graph.py
import os, json, asyncio, uuid, copy, ast, re
from typing import Any, Dict, Annotated, List, Union
from typing_extensions import TypedDict
from dotenv import load_dotenv

from langgraph.graph import StateGraph, START, END
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import GoogleGenerativeAIEmbeddings, GoogleGenerativeAI
from langchain_qdrant import Qdrant
from qdrant_client.models import Filter, FieldCondition, MatchValue
from langchain_core.runnables import Runnable
from pydantic import BaseModel, Field, ValidationError # Import ValidationError explicitly
from langchain_core.messages import ToolMessage, HumanMessage, AIMessage, ToolCall
from langchain_core.output_parsers import StrOutputParser
from langgraph.types import interrupt
from .tax_deductions import TaxCalculator 

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Essential checks after loading env vars
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable not set. Check your .env file.")
if not QDRANT_URL:
    raise ValueError("QDRANT_URL environment variable not set. Check your .env file.")
if not QDRANT_API_KEY:
    raise ValueError("QDRANT_API_KEY environment variable not set. Check your .env file.")

os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY # Ensure it's in os.environ for some langchain modules
os.environ["QDRANT_API_KEY"] = QDRANT_API_KEY # Ensure it's in os.environ for qdrant-client

EMBEDDING_MODEL = "models/text-embedding-004"
LLM_MODEL = "gemini-1.5-flash" 
llm = GoogleGenerativeAI(
    model=LLM_MODEL
)

COLLECTIONS = [
    "tax_law_chunks", "tax_rules_chunks", "capital_gain_cases",
    "cbdt_notifications", "itr_forms"
]

# --- STATE ---
class TaxState(TypedDict, total=False):
    messages: Annotated[list, add_messages] # Stores chat history (HumanMessage, AIMessage, ToolMessage)
    user_details: dict                   # Structured data provided by the user
    deduction_plan: dict                 # Initial plan of potential deductions
    eligible_deductions: dict            # Deductions for which data is available
    missing_data_questions: dict         # Fields still needed from user
    rag_results: dict                    # Results from RAG relevant to deductions
    reasoning: dict                      # Detailed reasoning for each deduction
    summary: str                         # Overall summary of deductions
    legal_basis: str                     # Legal citations and context
    verdict: str                         # Final comprehensive verdict

# ─── LLM CHAINS ──────────────────────────────────────────────────────────────

plan_prompt = PromptTemplate(
    input_variables=["user_details"],
    template="""
You are a tax assistant. Given these user details (JSON):
{user_details}

Identify ALL potential tax deductions applicable under Indian Income Tax law for a salaried individual (FY 2024-25, AY 2025-26).
For each potential deduction, return a JSON object where the key is the deduction name (use these exact keys: "standard_deduction", "section_80C_deduction", "section_80D_deduction", "section_24B_deduction", "section_80G_deduction", "section_80CCD1B_deduction", "section_80E_deduction", "section_80DD_deduction", "section_80TTA_deduction", "section_80TTB_deduction").
For each deduction, the value should be an object with:
- eligibility_criteria: a short description of the general eligibility.
- required_fields: a list of specific fields from user_details (e.g., 'salary', 'tax_regime', 'health_insurance_premium', 'donation_amount', 'housing_loan_interest', 'investments.80C_investments', 'investments.nps_contribution', 'education_loan_interest', 'disability_details.is_disabled', 'disability_details.type', 'other_income.interest_from_savings', 'other_income.fixed_deposit_interest', 'age_self', 'age_parents', 'property_status', 'residential_status', 'filing_status', 'employment_status') that are crucial for determining eligibility and calculating the amount. Use dot notation for nested fields.
- query: a short free-text query to fetch relevant legal context for that specific deduction.

Be comprehensive and list all basic deductions, even if the user_details currently lack the required fields.
For example, if user_details does not contain 'investments.nps_contribution', you should still include "section_80CCD1B_deduction" but specify 'investments.nps_contribution' as a 'required_field'.

Respond with ONLY the JSON object.
""".strip(),
)
plan_chain: Runnable = plan_prompt | llm | JsonOutputParser()


question_formatter_prompt = PromptTemplate(
    input_variables=["fields"],
    template="""
You are an expert tax assistant. Your task is to convert a given list of EXACT technical field names into a clear, user-friendly list of questions for a person in India.
You MUST ONLY ask questions for the fields PROVIDED in the 'fields' list. Do NOT add any other questions or general inquiries.
Ask one question per field. Do not bundle them.

Example:
Input fields: ['health_insurance_premium', 'age_parents']
Output:
- What is the total health insurance premium you paid for yourself and your family (not including parents)?
- What are the ages of your parents?

---
Input fields to convert:
{fields}

Output:
""".strip(),
)

question_formatter_chain: Runnable = (
    question_formatter_prompt | llm | StrOutputParser()
)

query_analyzer_prompt = PromptTemplate(
    input_variables=["query"],
    template="""
Analyze the following tax deduction query and extract any explicit Indian Income Tax sections (e.g., "80C", "24B").
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
query_analyzer_chain: Runnable = query_analyzer_prompt | llm | JsonOutputParser()

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
reason_chain: Runnable = reason_prompt | llm | JsonOutputParser()


# Pydantic model for structured parsing of human input
class ParsedHumanInput(BaseModel):
    user_age: Union[int, None] = Field(None, description="Age of the user in years.")
    health_insurance_premium: Union[int, None] = Field(None, description="Health insurance premium paid by the user for self/family.")
    medical_expenses: Union[int, None] = Field(None, description="Medical expenses incurred by the user for self/family (if not covered by insurance).")
    parents_age: Union[List[int], None] = Field(None, description="Ages of the user's parents in years, as a list.")
    parents_health_insurance_premium: Union[int, None] = Field(None, description="Health insurance premium paid for parents.")
    parents_medical_expenses: Union[int, None] = Field(None, description="Medical expenses incurred for parents (if not covered by insurance).")
    housing_loan_interest: Union[int, None] = Field(None, description="Interest paid on housing loan for a self-occupied property.")
    investments_80C: Union[int, None] = Field(None, description="Total investments under Section 80C (e.g., EPF, PPF, Life Insurance premium, Home Loan Principal repayment).")
    nps_contribution: Union[int, None] = Field(None, description="Contribution to National Pension System (NPS).")
    education_loan_interest: Union[int, None] = Field(None, description="Interest paid on education loan.")
    donation_amount: Union[int, None] = Field(None, description="Amount donated by the user to a qualifying institution.")
    interest_from_deposits: Union[int, None] = Field(None, description="Total interest earned from fixed deposits and other similar interest-bearing accounts.")
    interest_from_savings: Union[int, None] = Field(None, description="Total interest earned from savings accounts.")
    is_disabled: Union[bool, None] = Field(None, description="True if the user is registered as a person with a disability, False otherwise.")
    disability_type: Union[str, None] = Field(None, description="Type of disability if applicable (e.g., 'normal_disability', 'severe_disability').")
    residential_status: Union[str, None] = Field(None, description="Tax residential status in India (e.g., Resident and Ordinarily Resident).")
    filing_status: Union[str, None] = Field(None, description="Filing status for income tax purposes (e.g., Single, Married, Individual, Senior Citizen).")
    employment_status: Union[str, None] = Field(None, description="The user's employment status (e.g., salaried, self-employed).")


# Chain for parsing human input
_schema = json.dumps(ParsedHumanInput.model_json_schema(), indent=2)
_escaped_schema = _schema.replace("{", "{{").replace("}", "}}")

# 2) Recreate your prompt with only the {user_input} placeholder
parse_human_input_prompt = PromptTemplate(
    input_variables=["user_input"],
    template=(
        "You are an AI assistant that extracts specific financial and personal details "
        "from a user's natural language input. Parse the user's response to the questions asked. "
        "Only extract the amounts for the fields listed in the JSON schema. "
        "If a field is not mentioned, cannot be clearly identified, or has a value of zero, set its value to null. "
        "Convert all monetary values and ages to integers. "
        "For 'is_disabled', convert 'yes'/'no' phrases to `true`/`false`. "
        "For 'employment_status', infer from phrases like 'primary source of income is salary' to 'salaried'. "
        "Do not assume any values.\n\n"
        "User's response: {user_input}\n\n"
        "Respond with ONLY a single, valid JSON object that adheres to the following schema:\n"
        "```json\n"
        f"{_escaped_schema}\n"
        "```"
    )
)

# rebuild the chain
parse_human_input_chain = (
    parse_human_input_prompt
    | llm
    | JsonOutputParser(pydantic_object=ParsedHumanInput)
)

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

# ─── TOOLS ──────────────────────────────────────────────────────────────────
# This tool is called by the `ask_for_data_node` to prompt the user.
@tool()
def human_assistance_tool(query: str) -> str:
    """
    Interrupts the graph to ask the user for more information.
    The 'query' is the question presented to the user. The graph will halt
    execution until it is resumed with the user's input.
    """
    # LangGraph's ToolNode will capture the return value of this tool
    # and use it as the content of a ToolMessage.
    print(f"Tool Called: human_assistance_tool. Graph will now interrupt.")
    human_input = interrupt(query)
    return human_input 

# ─── NODE FUNCTIONS ──────────────────────────────────────────────────────────

def get_nested(data: dict, path: str):
    """Helper to get a nested field using dot notation."""
    parts = path.split('.')
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
    response = plan_chain.invoke({
        "user_details": json.dumps(user_details)
    })
    # Ensure 'messages' is initialized if it's the very first node
    if "messages" not in state:
        state["messages"] = []
    
    # LangGraph's add_messages handles appending, so just return new messages
    return {"deduction_plan": response, "messages": [AIMessage(content="Generated initial deduction plan.")]}

def clarify_node(state: TaxState) -> dict:
    """Detect missing fields by checking the original plan against user_details."""
    print("--- Executing Node: Clarify ---")
    user_details = state["user_details"]

    deduction_plan = state["deduction_plan"]

    missing = {}
    
    # Iterate through each planned deduction
    for name, info in deduction_plan.items():
        missing_fields_for_deduction = []
        
        # Special handling for Section 80DD based on is_disabled status
        if name == "section_80DD_deduction":
            is_disabled = get_nested(user_details, 'disability_details.is_disabled')
            
            # If 'is_disabled' is not yet known, ask for it
            if is_disabled is None:
                missing_fields_for_deduction.append('disability_details.is_disabled')
            elif is_disabled is True: # If user is disabled, and type is missing, ask for type
                if get_nested(user_details, 'disability_details.type') is None:
                    missing_fields_for_deduction.append('disability_details.type')
            # If is_disabled is False, we do not need to ask for disability_details.type

        else: # Normal handling for other deductions
            # Check each required field for the current deduction
            for field_path in info.get("required_fields", []):
                # Using get_nested to safely check for nested fields
                if get_nested(user_details, field_path) is None:
                    missing_fields_for_deduction.append(field_path)
        
        if missing_fields_for_deduction:
            missing[name] = missing_fields_for_deduction
    
            
    return {"missing_data_questions": missing}

def ask_for_data_node(state: TaxState) -> Dict[str, Any]:
    """
    Identifies missing data and uses an LLM to formulate user-friendly questions.
    Generates an AIMessage with a ToolCall to human_assistance_tool.
    """
    print("--- Executing Node: Ask for Data ---")
    missing_questions = state.get("missing_data_questions", {})
    if not missing_questions:
        print("No missing questions found, skipping ask_for_data_node.")
        return {} # Should not be reached if conditional edge is correct

    # Extract unique, flat list of technical field names (e.g., 'user_age', 'health_insurance_premium')
    fields_to_ask_set = set()
    for fields_list in missing_questions.values():
        for field_path in fields_list:
            # Get the last part of the dot-notation path
            fields_to_ask_set.add(field_path.split('.')[-1])
    
    fields_to_ask = sorted(list(fields_to_ask_set))
    print(f"Fields to ask LLM for formatting: {fields_to_ask}")

    # Use the new LLM chain to generate friendly questions
    formatted_questions = question_formatter_chain.invoke({"fields": str(fields_to_ask)})
    print(f"Formatted questions from LLM: {formatted_questions}")

    message_to_user = (
        "To give you the most accurate tax advice, I need a few more details. Please provide answers to the following:\n\n"
        f"{formatted_questions}\n\n"
        "You can type your answer in a single message, like: 'My age is 35, I paid 25000 for health insurance and my NPS contribution was 50000.'"
    )
    print(f"Message to user for human assistance tool: {message_to_user}")

    # Return an AIMessage containing a ToolCall to the human_assistance_tool.
    # This will cause the ToolNode to execute human_assistance_tool, which then causes LangGraph to interrupt.
    tool_call_id = str(uuid.uuid4()) # Generate a unique ID for this tool call
    return {
        "messages": [
            AIMessage(
                content="", # Content can be empty as the query is in tool_calls
                tool_calls=[
                    ToolCall(
                        name="human_assistance_tool",
                        args={"query": message_to_user},
                        id=tool_call_id # Crucial for resuming the graph
                    )
                ]
            )
        ]
    }

def parse_human_input_node(state: TaxState) -> Dict[str, Any]:
    """
    Parses the user's natural language input (from a ToolMessage), and correctly merges the new
    information with existing user details.
    """
    print("--- Executing Node: Parse Human Input ---")

    messages = state.get("messages", [])
    # Find the latest ToolMessage from the human that's a response to human_assistance_tool
    pattern = r"ToolMessage\(content='(.*?)',\s*name='human_assistance_tool'"

    raw_user_input = None  # Ensure it's declared

    for msg in reversed(messages):
        if isinstance(msg, ToolMessage) and msg.name == "human_assistance_tool":
            try:
                match = re.search(pattern, msg.content)
                if match:
                    extracted_input = match.group(1)
                    raw_user_input = json.dumps({  # ✅ Convert dict to JSON string
                        "data": extracted_input
                    })
                    print(f"Extracted raw user input from ToolMessage (as JSON): '{raw_user_input}'")
                    break
            except Exception as e:
                print(f"Failed to parse message: {e}")
                continue

    if not raw_user_input:
        print("Warning: No human input found in ToolMessage. Skipping parsing.")
        return {"messages": [AIMessage(content="No input received. Please provide the requested information.")]}


    print(f"Raw user input for parsing: '{raw_user_input}'")
    
    # Attempt to parse raw_user_input if it looks like a JSON string from Command.resume wrapper
    # This ensures flexibility if the external system wraps the input
    try:
        if isinstance(raw_user_input, str) and raw_user_input.strip().startswith('{') and raw_user_input.strip().endswith('}'):
            parsed_raw_input_dict = json.loads(raw_user_input)
            if "data" in parsed_raw_input_dict and isinstance(parsed_raw_input_dict["data"], str):
                user_input_to_parse = parsed_raw_input_dict["data"] # Extract the actual user input string
                print(f"Extracted actual user input from JSON wrapper: '{user_input_to_parse}'")
            else:
                user_input_to_parse = raw_user_input # Use original if 'data' key missing or not string
                print(f"Warning: JSON wrapper found but 'data' key missing or not string. Processing original: '{user_input_to_parse}'")
        else:
            user_input_to_parse = raw_user_input
            print(f"No JSON wrapper detected. Processing raw user input: '{user_input_to_parse}'")
    except json.JSONDecodeError:
        user_input_to_parse = raw_user_input
        print(f"Warning: Input looked like JSON but was malformed. Processing as plain string: '{user_input_to_parse}'")


    try:
        # Use the LLM chain to parse the human's natural language response into structured data
        parsed_data = parse_human_input_chain.invoke({
            "user_input": user_input_to_parse
        })
        
        # Ensure parsed_data is an instance of ParsedHumanInput
        if not isinstance(parsed_data, ParsedHumanInput):
            # This should ideally be handled by JsonOutputParser(pydantic_object=...),
            # but as a fallback/debug, try manual conversion.
            print(f"DEBUG: LLM chain returned type {type(parsed_data)}. Attempting conversion to ParsedHumanInput.")
            if isinstance(parsed_data, dict):
                parsed_data = ParsedHumanInput(**parsed_data)
            else:
                raise TypeError(f"Expected ParsedHumanInput or dict from parser, got {type(parsed_data)}")

        print(f"Parsed data from LLM (structured): {parsed_data.model_dump_json(indent=2)}")
        
        # Create a deepcopy of user_details to avoid direct mutation issues in LangGraph
        updated_user_details = copy.deepcopy(state.get("user_details", {}))
        
        print(f"Original user details before merge: {updated_user_details}")

        # Helper to set nested fields, creating dictionaries if they don't exist
        def set_nested_field(data: dict, path: str, value: Any):
            parts = path.split('.')
            current = data
            for part in parts[:-1]:
                current = current.setdefault(part, {})
            current[parts[-1]] = value

        # Iterate through the newly parsed data and update the user_details dictionary
        if parsed_data.user_age is not None:
            updated_user_details["age_self"] = parsed_data.user_age
            updated_user_details["user_age"] = parsed_data.user_age 
        if parsed_data.health_insurance_premium is not None:
            set_nested_field(updated_user_details, "health_insurance_premium", parsed_data.health_insurance_premium)
        if parsed_data.medical_expenses is not None:
            set_nested_field(updated_user_details, "medical_expenses", parsed_data.medical_expenses)
        if parsed_data.parents_age is not None:
            # If multiple ages, take the max for senior citizen logic; otherwise use the single age
            updated_user_details["parents_age"] = max(parsed_data.parents_age) if parsed_data.parents_age else None
        if parsed_data.parents_health_insurance_premium is not None:
            set_nested_field(updated_user_details, "parents_health_insurance_premium", parsed_data.parents_health_insurance_premium)
        if parsed_data.parents_medical_expenses is not None:
            set_nested_field(updated_user_details, "parents_medical_expenses", parsed_data.parents_medical_expenses)
        if parsed_data.housing_loan_interest is not None:
            set_nested_field(updated_user_details, "housing_loan_interest", parsed_data.housing_loan_interest)
        if parsed_data.investments_80C is not None:
            set_nested_field(updated_user_details, "investments.80C_investments", parsed_data.investments_80C)
        if parsed_data.nps_contribution is not None:
            set_nested_field(updated_user_details, "investments.nps_contribution", parsed_data.nps_contribution)
        if parsed_data.education_loan_interest is not None:
            set_nested_field(updated_user_details, "education_loan_interest", parsed_data.education_loan_interest)
        if parsed_data.donation_amount is not None:
            set_nested_field(updated_user_details, "donation_amount", parsed_data.donation_amount)
        if parsed_data.interest_from_deposits is not None:
            set_nested_field(updated_user_details, "other_income.fixed_deposit_interest", parsed_data.interest_from_deposits)
        if parsed_data.interest_from_savings is not None:
            set_nested_field(updated_user_details, "other_income.interest_from_savings", parsed_data.interest_from_savings)
        if parsed_data.is_disabled is not None:
            set_nested_field(updated_user_details, "disability_details.is_disabled", parsed_data.is_disabled)
            if parsed_data.is_disabled and parsed_data.disability_type:
                 set_nested_field(updated_user_details, "disability_details.type", parsed_data.disability_type)
            elif parsed_data.is_disabled and not parsed_data.disability_type:
                 set_nested_field(updated_user_details, "disability_details.type", "normal_disability") # Default if enabled
        if parsed_data.residential_status is not None:
            updated_user_details["residential_status"] = parsed_data.residential_status
        if parsed_data.filing_status is not None:
            updated_user_details["filing_status"] = parsed_data.filing_status
            if "individual" in parsed_data.filing_status.lower() or "self" in parsed_data.filing_status.lower():
                updated_user_details["tax_regime"] = "old" 
        if parsed_data.employment_status is not None:
            updated_user_details["employment_status"] = parsed_data.employment_status

        # Re-evaluate senior citizen status based on updated user_age
        if 'age_self' in updated_user_details:
            updated_user_details["is_senior_citizen"] = updated_user_details["age_self"] >= 60
        
        print(f"Updated user details after merging: {updated_user_details}")
        
        return {
            "user_details": updated_user_details,
            "messages": [AIMessage(content="Successfully parsed and updated user details.")]
        }

    except ValidationError as e:
        print(f"Validation Error during parsing human input: {e.errors()}")
        return {
            "messages": [AIMessage(content=f"I couldn't parse your input due to validation errors. Please ensure you are providing numeric values for amounts and ages. Error: {e.errors()}")],
            # This will cause it to go back to clarify and potentially re-ask
            "user_details": state.get("user_details", {}) # Preserve existing user details
        }
    except Exception as e:
        print(f"General Error parsing human input: {e}")
        import traceback
        traceback.print_exc()
        return {
            "messages": [AIMessage(content="An unexpected error occurred while processing your input. Could you please try again?")],
            "user_details": state.get("user_details", {}) # Preserve existing user details
        }

def filter_node(state: TaxState) -> dict:
    """Check which deductions the user is eligible for based on available data."""
    print("--- Executing Node: Filter ---")
    user_details = state["user_details"]
    deduction_plan = state["deduction_plan"]
    eligible = {}
    
    # Create a TaxCalculator instance with the current user_details
    calculator = TaxCalculator(user_details)

    for k, v in deduction_plan.items():
        # Check if all required fields are present in the user_details
        all_fields_present = True
        for field in v.get("required_fields", []):
            if get_nested(user_details, field) is None:
                all_fields_present = False
                break
        
        if all_fields_present:
            # If data is present, attempt to calculate using TaxCalculator
            calc_method_name = f"calculate_{k}"
            if hasattr(calculator, calc_method_name) and callable(getattr(calculator, calc_method_name)):
                calculated_deduction = getattr(calculator, calc_method_name)()
                eligible[k] = calculated_deduction
            else:
                # Fallback if a specific calculation method isn't found
                eligible[k] = v # Keep the plan info for this deduction
        else:
            # If data is missing, we don't include it in 'eligible_deductions'
            # but it was handled by clarify_node and will be re-asked if needed.
            pass
            
    return {"eligible_deductions": eligible, "messages": [AIMessage(content="Filtered eligible deductions.")]}

async def analyze_query_node(state: TaxState) -> dict:
    """Analyzes each deduction query to extract structured search parameters."""
    print("--- Executing Node: Analyze Query ---")
    deduction_plan = state["deduction_plan"] # Use deduction_plan to get all queries
    analyzed_queries = {}
    
    analysis_tasks = []
    deduction_names = []

    for name, info in deduction_plan.items():
        query = info.get("query")
        if query:
            analysis_tasks.append(query_analyzer_chain.ainvoke({"query": query})) # Use ainvoke for LLM chain
            deduction_names.append(name)
        else:
            analyzed_queries[name] = {"sections": [], "rules": []} # No query provided

    results_from_analysis = await asyncio.gather(*analysis_tasks)

    for i, name in enumerate(deduction_names):
        analyzed_queries[name] = results_from_analysis[i]
            
    return {"analyzed_query": analyzed_queries, "messages": [AIMessage(content="Analyzed initial user query for RAG.")]}

async def rag_node(state: TaxState) -> dict:
    """
    Performs a multi-stage, metadata-filtered retrieval for each deduction asynchronously.
    """
    print("--- Executing Node: RAG (Filtered Retrieval) ---")
    deduction_plan = state["deduction_plan"] # Use deduction_plan, as rag_node should process all planned deductions
    analyzed_queries = state.get("analyzed_query", {})
    rag_results = {}

    all_deduction_rag_tasks = []
    deduction_names_for_tasks = []

    for name, info in deduction_plan.items(): # Iterate through all planned deductions
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
            # High-precision search in laws and rules (async)
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

    return {"rag_results": rag_results, "messages": [AIMessage(content="Retrieved relevant legal contexts.")]}

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
            if get_nested(user_details, field) is None:
                all_fields_present = False
                break

        if not all_fields_present:
            # If data is missing, mark as N/A and provide specific questions
            missing_fields_list_paths = state["missing_data_questions"].get(name, [])
            # Convert paths to more readable names for the user
            readable_missing_fields = [
                field.replace("investments.", "").replace("disability_details.", "").replace("other_income.", "")
                for field in missing_fields_list_paths
            ]

            result = {
                "amount": "N/A",
                "summary": f"Data missing for this deduction. Please provide: {', '.join(readable_missing_fields) if readable_missing_fields else 'required information'}.",
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

    return {"reasoning": reasoning, "messages": [AIMessage(content="Generated reasoning for eligible deductions.")]}

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
    gross_income = calculator.calculate_gross_income()
    total_taxable_income = gross_income - total_deductions
    if total_taxable_income < 0:
        total_taxable_income = 0 # Taxable income cannot be negative

    # Calculate Tax Liability
    tax_liability = calculator.calculate_tax_liability(total_taxable_income)

    # Return in the same format as other nodes
    return {
        "total_deductions": total_deductions,
        "total_taxable_income": total_taxable_income,
        "tax_liability": tax_liability,
        "messages": [
            AIMessage(
                content=(
                    f"Calculated totals:\n"
                    f"- Total Deductions: ₹{total_deductions:,.2f}\n"
                    f"- Taxable Income: ₹{total_taxable_income:,.2f}\n"
                    f"- Tax Liability: ₹{tax_liability:,.2f}"
                )
            )
        ]
    }

def summary_node(state: TaxState) -> dict:
    """Summarize all deductions and amounts."""
    print("--- Executing Node: Summary ---")
    reasoning = state["reasoning"]
    lines = []
    total_deduction_amount = 0.0

    for k in sorted(reasoning.keys()):
        v = reasoning[k]
        deduction_amount_str = v.get('amount', 'N/A')
        summary_text = v.get('summary', 'No summary available')
        
        # Attempt to parse numeric amount if available and add to total
        try:
            # Remove currency symbols and commas, then convert to float
            numeric_val = float(deduction_amount_str.replace('₹', '').replace(',', ''))
            total_deduction_amount += numeric_val
        except (ValueError, TypeError):
            pass # Ignore if not a valid number or N/A

        lines.append(f"- **{k.replace('_', ' ').title()}**: {deduction_amount_str} ({summary_text})")
    
    final_summary_text = "\n".join(lines)
    final_summary_text += f"\n\n**Estimated Total Deductible Amount**: ₹{total_deduction_amount:,.2f}"

    return {"summary": final_summary_text, "messages": [AIMessage(content="Generated overall summary of deductions.")]}

def legal_node(state: TaxState) -> dict:
    """Summarize the legal basis (sections/cases) for deductions."""
    print("--- Executing Node: Legal ---")
    reasoning = state["reasoning"]
    lines = []
    for k in sorted(reasoning.keys()):
        v = reasoning[k]
        citations = v.get('citations', [])
        if citations:
            lines.append(f"- **{k.replace('_', ' ').title()}**: {', '.join(citations)}")
        else:
            lines.append(f"- **{k.replace('_', ' ').title()}**: No specific citations available.")
    return {"legal_basis": "\n".join(lines), "messages": [AIMessage(content="Compiled legal basis.")]}

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
    return {"verdict": verdict, "messages": [AIMessage(content="Final tax deduction verdict generated.")]}

# ─── GRAPH DEFINITION ────────────────────────────────────────────────────────
def create_tax_graph(checkpointer=None):
    graph_builder = StateGraph(TaxState)

    # Add all nodes
    graph_builder.add_node("plan_node", plan_node)
    graph_builder.add_node("clarify_node", clarify_node)
    # The ToolNode will execute human_assistance_tool and cause interruption
    graph_builder.add_node("ask_for_data_node", ask_for_data_node)
    graph_builder.add_node("human_interruption", ToolNode([human_assistance_tool])) # This node directly calls the tool
    graph_builder.add_node("parse_human_input_node", parse_human_input_node)
    graph_builder.add_node("filter_node", filter_node)
    graph_builder.add_node("analyze_query_node", analyze_query_node)
    graph_builder.add_node("rag_node", rag_node)
    graph_builder.add_node("reason_node", reason_node)
    graph_builder.add_node("calculate_totals_node", calculate_totals_node)
    graph_builder.add_node("summary_node", summary_node)
    graph_builder.add_node("legal_node", legal_node)
    graph_builder.add_node("verdict_node", verdict_node)

    # Set the entry point
    graph_builder.set_entry_point("plan_node")
    graph_builder.add_edge("plan_node", "clarify_node")

    # Conditional edge from clarify_node: checks if more data is needed
    def should_ask_for_data(state: TaxState) -> str:
        # Check if any deduction still has missing questions
        for deduction_questions in state.get("missing_data_questions", {}).values():
            if deduction_questions:
                print("DEBUG: Missing data detected. Transitioning to ask_for_data_node.")
                return "ask_user_for_input"
        print("DEBUG: No missing data. Proceeding to filter_node.")
        return "proceed_to_filter"

    graph_builder.add_conditional_edges(
        "clarify_node",
        should_ask_for_data,
        {"ask_user_for_input": "ask_for_data_node", "proceed_to_filter": "filter_node"},
    )

    # After ask_for_data_node (which contains the ToolNode for human_assistance_tool),
    # the graph will interrupt. When resumed, it will go to parse_human_input_node.
    graph_builder.add_edge("ask_for_data_node", "human_interruption") 
    graph_builder.add_edge("human_interruption", "parse_human_input_node")
    # After parsing the human input, loop back to re-evaluate the clarification
    # This is crucial for iterating on data collection.
    graph_builder.add_edge("parse_human_input_node", "clarify_node")

    # Standard flow after all data is gathered and clarified
    graph_builder.add_edge("filter_node", "analyze_query_node")
    graph_builder.add_edge("analyze_query_node", "rag_node")
    graph_builder.add_edge("rag_node", "reason_node")
    graph_builder.add_edge("reason_node", "calculate_totals_node") # New edge
    graph_builder.add_edge("calculate_totals_node", "summary_node") # New edge
    graph_builder.add_edge("summary_node", "legal_node")
    graph_builder.add_edge("legal_node", "verdict_node")
    graph_builder.add_edge("verdict_node", END)

    # Compile the graph with the checkpointer
    graph = graph_builder.compile(checkpointer=checkpointer)
    return graph

# Removed if __name__ == "__main__" block to prevent accidental execution when imported.
# The `main.py` script will handle direct graph invocation for testing purposes.