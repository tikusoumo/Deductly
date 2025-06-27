# backend/services/chat_service.py
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from fastapi import HTTPException, status
from bson import ObjectId

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, BaseMessage
from langgraph.checkpoint.mongodb.aio import AsyncMongoDBSaver
from langgraph.types import Command # Import Command for graph resumption
from rag_pipeline.main_graph import create_tax_graph  # this should return your graph with checkpointer
from services.database_service import db_service
from rag_pipeline.llm_setup import conversation_chain 

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
# from rag_pipeline.llm_setup import conversation_chain # This will be discarded for graph usage

# Assuming main_graph is directly importable from rag_pipeline
try:
    from rag_pipeline.main_graph import create_tax_graph 
    print("LangGraph 'graph' imported successfully in chat_service.")
except ImportError as e:
    print(f"Error importing LangGraph 'graph' in chat_service: {e}")
    raise ImportError(f"Missing LangGraph: {e}. Please ensure backend/rag_pipeline/main_graph.py exists and defines 'graph'.")


# --- Helper Function (from app.py) ---
def process_graph_output(graph_state: Dict[str, Any]) -> Tuple[str, bool, Optional[str]]:
    """
    Inspects the final state of a graph run to determine the outcome.

    Returns:
        - bot_response (str): The message to send to the user.
        - awaiting_human_input (bool): True if the graph is interrupted.
        - tool_call_id (str | None): The ID of the tool call if interrupted.
    """
    bot_response = "An unexpected error occurred. Please try again."
    awaiting_human_input = False
    tool_call_id_for_resume = None

    messages = graph_state.get("messages", [])

    # Check for a final verdict first (assuming it's a desired end state)
    if verdict := graph_state.get("verdict"):
        bot_response = verdict
        awaiting_human_input = False
    # If no verdict, check if the last message is an interruption tool call
    elif messages and isinstance(messages[-1], AIMessage):
        last_message = messages[-1]
        if last_message.tool_calls:
            for tool_call in last_message.tool_calls:
                # Assuming 'human_assistance_tool' is the one that causes interruption for human input
                if tool_call.get("name") == "human_assistance_tool":
                    awaiting_human_input = True
                    # The query argument of the tool call is the question for the user
                    bot_response = tool_call.get("args", {}).get("query", "I need more information. Please tell me more.")
                    tool_call_id_for_resume = tool_call.get("id")
                    break # Found the interruption, no need to check other tool calls
        else:
            # Regular AIMessage without tool calls
            bot_response = last_message.content
    elif messages and isinstance(messages[-1], HumanMessage):
        # If the last message is a HumanMessage, it means the graph received input
        # but didn't produce an AI response (yet or for this turn).
        # This could be an intermediate state.
        bot_response = "Received your message. Analyzing..." # Or some other appropriate intermediate response
        awaiting_human_input = False
    elif messages and isinstance(messages[-1], ToolMessage):
        # If the last message is a ToolMessage, it means the graph processed a tool's output
        # but might still be processing or waiting for next steps.
        bot_response = "Processed tool output. Please wait for the next steps."
        awaiting_human_input = False

    return bot_response, awaiting_human_input, tool_call_id_for_resume

class ChatService:
    graph_with_mongo = None  # LangGraph with checkpointing

    async def initialize(self):
        if not ChatService.graph_with_mongo:
            db = db_service.get_database()
            checkpointer = AsyncMongoDBSaver(db)
            ChatService.graph_with_mongo = create_tax_graph(checkpointer=checkpointer)
            
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
        Invokes LangGraph for initial analysis and uses the raw verdict as the assistant's message.
        """
        sessions_collection = db_service.get_session_collection()
        user_id_obj = ObjectId(user_id)
        # Generate a unique session ID for LangGraph's thread_id
        session_id = str(ObjectId()) 
        config = {"configurable": {"thread_id": session_id}}

        print(f"[{session_id}] Invoking LangGraph for initial tax analysis...")
        initial_graph_input = {
            "user_details": input_data.user_details,
            "messages": [HumanMessage(content="Calculate my tax deductions based on the provided details.")]
        }
        
        # Use ainvoke: it runs until the graph finishes or interrupts
        final_state = await ChatService.graph_with_mongo.ainvoke(initial_graph_input, config)

        # Process the result of the graph run
        bot_response, awaiting_human_input, tool_call_id = process_graph_output(final_state)

        # Build chat history for the frontend
        chat_history = [
            ChatMessage(role="user", content="Here are my initial tax details."),
            ChatMessage(role="assistant", content=bot_response, tool_call_id=tool_call_id)
        ]

        current_time = datetime.now()
        session_title = f"Tax Chat {current_time.strftime('%Y-%m-%d %H:%M')}"
            
        new_session = {
            "_id": ObjectId(session_id), # Store as ObjectId
            "user_id": user_id_obj,
            "title": session_title,
            "created_at": current_time,
            "updated_at": current_time,
            "chat_history": [msg.model_dump() for msg in chat_history], # Store chat messages as dicts
            "initial_tax_details": input_data.user_details,
            "awaiting_human_input": awaiting_human_input, # Store the state
            "langgraph_thread_id": session_id # This links to the LangGraph checkpointer
        }

        inserted_session = await sessions_collection.insert_one(new_session)
        
        print(f"[{session_id}] New session created. Awaiting Human Input: {awaiting_human_input}")

        return StartSessionResponse(
            message="New tax session started",
            session_id=str(inserted_session.inserted_id),
            bot_response=bot_response,
            chat_history=chat_history,
            awaiting_human_input=awaiting_human_input
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

        config = {"configurable": {"thread_id": session_id}} 

        final_state = None # Initialize final_state for clarity
        bot_response_content = None
        tool_call_id = None
        awaiting_human_input = False
        if input_data.is_interruption_response:
            # Find the last AI message in chat history (excluding the current user's message)
            # that contained a tool_call (which would be the interruption for human assistance)
            last_ai_message_with_tool_call = None
            # Iterate backwards, excluding the just-added user message
            for msg in reversed(chat_history_messages[:-1]): 
                # Check if it's an assistant message and has a tool_call_id indicating an interruption
                if msg.role == "assistant" and msg.tool_call_id:
                    last_ai_message_with_tool_call = msg
                    break

            if not last_ai_message_with_tool_call or not last_ai_message_with_tool_call.tool_call_id:
                print(f"[{session_id}] Error: is_interruption_response is True but no active tool call found to respond to.")
                raise HTTPException(status_code=400, detail="No active human assistance request found to respond to. Please start a new query or check your input.")

            tool_call_id_to_resume = last_ai_message_with_tool_call.tool_call_id

            # Create a ToolMessage. This is the user's answer to the interrupted tool call.
            tool_message_object = ToolMessage(
                content=input_data.message,
                tool_call_id=tool_call_id_to_resume,
                name="human_assistance_tool" # Assuming this is the tool that caused the interruption
            )
            
            # Create the Command object for resumption.
            # The 'data' field of the 'resume' command holds the ToolMessage.
            resume_command = Command(
                resume={
                    "data": tool_message_object
                }
            )
            
            print(f"[{session_id}] Resuming graph with ToolMessage for tool_call_id: {tool_call_id_to_resume}")
            
            # Pass the resume_command to ainvoke
            final_state = await ChatService.graph_with_mongo.ainvoke(
                resume_command, 
                config
            )
            
        else:
            # --- START OF MODIFIED CODE FOR NORMAL MESSAGES ---
            print(f"Generating chatbot response for session {session_id} using direct conversation_chain...")
            
            # Convert chat_history_messages (ChatMessage models) to LangChain's BaseMessage format
            lc_chat_history = []
            for msg in chat_history_messages:
                if msg.role == "user":
                    lc_chat_history.append(HumanMessage(content=msg.content))
                elif msg.role == "assistant":
                    lc_chat_history.append(AIMessage(content=msg.content))
                # If you have ToolMessages in your history that conversation_chain might need, include them
                elif msg.role == "tool" and msg.tool_call_id and msg.name:
                    lc_chat_history.append(ToolMessage(content=msg.content, tool_call_id=msg.tool_call_id, name=msg.name))
            
            # Call the direct conversation_chain
            bot_response_content = (await conversation_chain.ainvoke(
                {"chat_history": lc_chat_history, "user_input": input_data.message}
            )).content

            # For direct LLM calls, interruption is not expected and there's no tool call ID
            awaiting_human_input = False
            tool_call_id = None 
            # --- END OF MODIFIED CODE FOR NORMAL MESSAGES ---
        if bot_response_content is None:
            bot_response_content = final_state.get("verdict", "An unexpected error occurred. Please try again.")
        # Add the bot's response to the chat history
        new_bot_message = ChatMessage(role="assistant", content=bot_response_content, tool_call_id=tool_call_id)
        chat_history_messages.append(new_bot_message)

        await sessions_collection.update_one(
            {"_id": session_obj_id},
            {"$set": {
                "chat_history": [msg.model_dump() for msg in chat_history_messages],
                "updated_at": datetime.now(),
                "awaiting_human_input": awaiting_human_input # Update the session's interruption status
            }}
        )

        print(f"Session {session_id} updated with new message. Awaiting Human Input: {awaiting_human_input}")
        return SendMessageResponse(
            message="Message sent",
            bot_response=bot_response_content,
            updated_chat_history=chat_history_messages,
            awaiting_human_input=awaiting_human_input,
            session_id=session_id
        )
chat_service = ChatService()