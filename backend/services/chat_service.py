# backend/services/chat_service.py
from datetime import datetime
from typing import Dict, Any, List
from fastapi import HTTPException, status
from bson import ObjectId

from langchain_core.messages import HumanMessage, AIMessage

from models.chat_message_model import (
    InitialTaxDetailsInput,
    ChatMessageInput,
    ChatMessage,
    ChatSessionResponse,
    ChatSessionSummary,
    StartSessionResponse,
    SendMessageResponse
)
from services.database_service import db_service
from rag_pipeline.llm_setup import conversation_chain
# Assuming main_graph is directly importable from rag_pipeline
try:
    from rag_pipeline.main_graph import graph 
    print("LangGraph 'graph' imported successfully in chat_service.")
except ImportError as e:
    print(f"Error importing LangGraph 'graph' in chat_service: {e}")
    raise ImportError(f"Missing LangGraph: {e}. Please ensure backend/rag_pipeline/main_graph.py exists and defines 'graph'.")


class ChatService:
    async def get_user_chat_sessions(self, user_id: str) -> List[ChatSessionSummary]:
        """Retrieves all chat sessions for a given user."""
        sessions_collection = db_service.get_session_collection()
        chats = []
        async for session_doc in sessions_collection.find({"user_id": ObjectId(user_id)}).sort("updated_at", -1):
            session_data = dict(session_doc)
            session_data['id'] = str(session_data.pop('_id')) 
            
            chats.append(ChatSessionSummary(**session_data))
        return chats

    async def get_chat_session_by_id(self, session_id: str, user_id: str) -> ChatSessionResponse:
        """Retrieves a specific chat session by ID for a given user."""
        sessions_collection = db_service.get_session_collection()
        
        session_obj_id = ObjectId(session_id)
        user_id_obj = ObjectId(user_id)

        session_doc = await sessions_collection.find_one({"_id": session_obj_id, "user_id": user_id_obj})
        if not session_doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found or unauthorized.")
        
        # Convert the Motor document to a standard Python dictionary
        session_data = dict(session_doc)
        # Explicitly map MongoDB's '_id' to Pydantic's 'id' field, converting ObjectId to string
        session_data['id'] = str(session_data.pop('_id'))
        # Ensure user_id is also a string, though it might already be, for consistency with Pydantic
        session_data['user_id'] = str(session_data['user_id'])

        # Convert chat_history list of dicts to list of ChatMessage Pydantic models
        # Ensure 'chat_history' key exists, provide empty list if not
        session_data['chat_history'] = [ChatMessage(**msg) for msg in session_data.get('chat_history', [])]

        # Return the Pydantic model by unpacking the prepared dictionary
        return ChatSessionResponse(**session_data)

    async def start_new_tax_session(self, input_data: InitialTaxDetailsInput, user_id: str) -> StartSessionResponse:
        """
        Starts a new tax deduction chat session.
        Invokes LangGraph for initial analysis and generates an initial bot response.
        """
        sessions_collection = db_service.get_session_collection()
        user_id_obj = ObjectId(user_id)

        print("Invoking LangGraph for initial tax analysis...")
        initial_state = {"user_details": input_data.user_details}
        final_result_graph = await graph.ainvoke(initial_state)
        verdict_text = final_result_graph.get("verdict", "No detailed tax verdict could be generated.")

        print("Generating initial chatbot response from verdict...")
        initial_prompt_for_llm = f"Please summarize the following tax deduction verdict in a friendly, conversational tone, highlighting key deductions and missing info: \n\n{verdict_text}"
        
        initial_bot_response_message = (await conversation_chain.ainvoke(
            {"chat_history": [], "user_input": initial_prompt_for_llm}
        )).content

        chat_history = [
            ChatMessage(role="assistant", content=initial_bot_response_message)
        ]

        current_time = datetime.now()
        session_title = f"Tax Chat {current_time.strftime('%Y-%m-%d %H:%M')}"
        
        new_session = {
            "user_id": user_id_obj,
            "title": session_title,
            "created_at": current_time,
            "updated_at": current_time,
            "chat_history": [msg.model_dump() for msg in chat_history], # Store dicts in DB
            "initial_tax_details": input_data.user_details
        }
        inserted_session = await sessions_collection.insert_one(new_session)
        session_id = str(inserted_session.inserted_id)

        print(f"New session created with ID: {session_id}")
        return StartSessionResponse(
            message="New tax session started",
            session_id=session_id,
            initial_bot_response=initial_bot_response_message,
            chat_history=chat_history
        )

    async def send_message_to_chat(self, session_id: str, input_data: ChatMessageInput, user_id: str) -> SendMessageResponse:
        """Sends a new message to an existing chat session and gets an LLM response."""
        sessions_collection = db_service.get_session_collection()

        session_obj_id = ObjectId(session_id)
        user_id_obj = ObjectId(user_id)

        session_doc = await sessions_collection.find_one({"_id": session_obj_id, "user_id": user_id_obj})
        if not session_doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found or unauthorized.")
        
        # Convert chat_history list of dicts to list of ChatMessage Pydantic models
        chat_history_messages = [ChatMessage(**msg) for msg in session_doc.get("chat_history", [])]
        
        new_user_message = ChatMessage(role="user", content=input_data.message)
        chat_history_messages.append(new_user_message)

        # Convert Pydantic ChatMessage objects to LangChain's HumanMessage/AIMessage format
        lc_chat_history = []
        for msg in chat_history_messages:
            if msg.role == "user":
                lc_chat_history.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                lc_chat_history.append(AIMessage(content=msg.content))

        print(f"Generating chatbot response for session {session_id}...")
        
        bot_response_content = (await conversation_chain.ainvoke(
            {"chat_history": lc_chat_history, "user_input": input_data.message}
        )).content

        new_bot_message = ChatMessage(role="assistant", content=bot_response_content)
        chat_history_messages.append(new_bot_message)

        await sessions_collection.update_one(
            {"_id": session_obj_id},
            {"$set": {
                "chat_history": [msg.model_dump() for msg in chat_history_messages],
                "updated_at": datetime.now()
            }}
        )

        print(f"Session {session_id} updated with new message.")
        return SendMessageResponse(
            message="Message sent",
            bot_response=bot_response_content,
            updated_chat_history=chat_history_messages
        )

chat_service = ChatService()