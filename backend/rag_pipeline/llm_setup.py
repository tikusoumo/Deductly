# backend/rag_pipeline/llm_setup.py
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from config.settings import settings

# Initialize the ChatGoogleGenerativeAI model
llm_chatbot_conversation = ChatGoogleGenerativeAI(
    model=settings.LLM_CHATBOT_MODEL, 
    temperature=settings.LLM_TEMPERATURE
)

# Define the conversation prompt for the chatbot
conversation_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a helpful AI tax assistant. Continue the conversation politely and provide tax information based on Indian Income Tax laws for FY 2024-25. If the user asks for a specific calculation or a new tax detail, you may prompt them for the necessary structured input if you cannot infer it from the conversation history. Always offer to help with further questions.
            Rules: 
            1. Always respond in a friendly and professional manner.
            2. If the user asks for a specific calculation, ask them to provide the necessary details.
            3. Do not helucinate by any chance.
            4. Do not entertain anything other than financial queries related to Indian Income Tax laws.
            5. If you're asked with something else rather than financial queries related to Indian Income Tax laws, politely inform the user that you are unable to provide that information.
            """
        ),
        MessagesPlaceholder(variable_name="chat_history"),
        ("user", "{user_input}"),
    ]
)

# Create the conversational chain by piping the prompt and the LLM
conversation_chain = conversation_prompt | llm_chatbot_conversation

print(f"LLM Chatbot model initialized: {settings.LLM_CHATBOT_MODEL}")