import React, { useEffect, useState } from "react";
import { ChatInterface } from "@/components/chat/ChatInterface";
import { useLocation } from "react-router-dom";

export const Chat: React.FC = () => {
  const location = useLocation();
  const [chatHistory, setChatHistory] = useState([]);
  const [sessionId, setSessionId] = useState<string | undefined>();

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const session_id = params.get("session_id");
    if (session_id) {
      setSessionId(session_id);

      // Fetch chat session data
      fetch(`http://localhost:8000/chats/${session_id}`, {
        headers: {
          "X-User-ID": localStorage.getItem("user_id") || "",
        },
      })
        .then((res) => res.json())
        .then((data) => {
          setChatHistory(data.chat_history || []);
        });
    }
  }, [location.search]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            Tax Consultations
          </h1>
          <p className="text-gray-600 mt-1">
            Chat with our AI tax advisor for personalized guidance.
          </p>
        </div>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-1 ">
        <div className="lg:col-span-2">
          <ChatInterface
            sessionId={sessionId}
            chatHistory={chatHistory}
            onNewSession={() => setSessionId(undefined)}
          />
        </div>
      </div>
    </div>
  );
};
