import React, { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { MessageCircle } from "lucide-react";
import { useNavigate } from "react-router-dom";

interface ChatSession {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export const History: React.FC = () => {
  const [chatSessions, setChatSessions] = useState<ChatSession[]>([]);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const user = localStorage.getItem("user")
      ? JSON.parse(localStorage.getItem("user") || "{}")
      : {};
    const userId = user.id || "";
    fetch("http://localhost:8000/chats", {
      headers: {
        "X-User-ID": userId,
      },
    })
      .then((res) => res.json())
      .then((data) => {
        if (Array.isArray(data)) {
          setChatSessions(data);
          setError(null);
        } else {
          setError("Failed to load chat history.");
          setChatSessions([]);
          console.error("Unexpected /chats response:", data);
        }
      })
      .catch((err) => {
        setError("Failed to load chat history.");
        setChatSessions([]);
        console.error("Fetch error:", err);
      });
  }, []);

  return (
    <div className="space-y-8">
      <h1 className="text-3xl font-bold text-gray-900">Chat History</h1>
      {error && <div className="text-red-500">{error}</div>}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {Array.isArray(chatSessions) &&
          chatSessions.map((session) => (
            <Card
              key={session.id}
              className="hover:shadow-lg transition-shadow cursor-pointer border border-gray-200"
              onClick={() => navigate(`/chat?session_id=${session.id}`)}
            >
              <CardContent className="p-5 flex items-center gap-4">
                <MessageCircle className="h-8 w-8 text-blue-600 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <h3 className="text-lg font-medium text-gray-900 truncate">
                    {session.title}
                  </h3>
                  <div className="text-xs text-gray-500 mt-1">
                    Last updated:{" "}
                    <span className="font-semibold text-lime-600">
                      {new Date(session.updated_at).toLocaleString()}
                    </span>
                  </div>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  className="transition-colors"
                  onClick={(e) => {
                    e.stopPropagation();
                    navigate(`/chat?session_id=${session.id}`);
                  }}
                >
                  View Chat
                </Button>
              </CardContent>
            </Card>
          ))}
      </div>
    </div>
  );
};
