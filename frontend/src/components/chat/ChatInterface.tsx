import React, { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Send, Bot, User, FileText, Loader2 } from "lucide-react";
import { Message as BaseMessage } from "@/types";

// Extend Message type to include optional tool_call_id
type Message = BaseMessage & {
  tool_call_id?: string | null;
};
import { Badge } from "@/components/ui/badge";

// Utility to convert markdown-like expressions to HTML for better formatting
function formatContent(content: string) {
  if (!content) return "";
  return (
    content
      // Headings (## or #) to bold and larger font
      .replace(
        /^##\s?(.*)$/gm,
        '<div style="font-weight:bold;font-size:1.1em;margin-top:0.7em;margin-bottom:0.3em;">$1</div>'
      )
      .replace(
        /^#\s?(.*)$/gm,
        '<div style="font-weight:bold;font-size:1.2em;margin-top:1em;margin-bottom:0.5em;">$1</div>'
      )
      // Bold (**text**)
      .replace(/\*\*(.*?)\*\*/g, "<b>$1</b>")
      // Inline code
      .replace(/`([^`]*)`/g, "<code>$1</code>")
      // Lists
      .replace(/^\s*[-*]\s?(.*)$/gm, "<li>$1</li>")
      // Remove other markdown
      .replace(/[_~]/g, "")
      // Remove emoji if you want
      .replace(/⚖️/g, "")
      // Wrap consecutive <li> in <ul>
      .replace(/(<li>[\s\S]*?<\/li>)/g, "<ul>$1</ul>")
  );
}

interface ChatInterfaceProps {
  sessionId?: string;
  chatHistory?: any[];
  onNewSession?: () => void;
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({
  sessionId,
  chatHistory = [],
  // onNewSession,
}) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Fetch chat history from backend when sessionId changes
  useEffect(() => {
    if (sessionId) {
      const user = localStorage.getItem("user")
        ? JSON.parse(localStorage.getItem("user") || "{}")
        : {};
      const userId = user.id || "";
      fetch(
        `http://localhost:8000/chats/${
          sessionId || localStorage.getItem("session_id")
        }`,
        {
          headers: {
            "Content-Type": "application/json",
            "X-User-ID": userId,
          },
        }
      )
        .then((res) => res.json())
        .then((data) => {
          if (Array.isArray(data.chat_history)) {
            setMessages(
              data.chat_history.map((msg: any, idx: number) => ({
                id: idx.toString(),
                content: msg.content,
                sender: msg.role === "assistant" ? "assistant" : "user",
                timestamp: msg.timestamp,
                type: "text",
                tool_call_id: msg.tool_call_id ?? null, // <-- include this!
              }))
            );
          }
        });
    } else if (chatHistory.length > 0) {
      setMessages(
        chatHistory.map((msg, idx) => ({
          id: idx.toString(),
          content: msg.content,
          sender: msg.role === "assistant" ? "assistant" : "user",
          timestamp: msg.timestamp,
          type: "text",
        }))
      );
    } else {
      setMessages([]);
    }
  }, [sessionId, chatHistory]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading || !sessionId) return;

    // Find the last assistant ("ai") message with a non-null tool_call_id
    const lastAssistantMsg = [...messages]
      .reverse()
      .find((msg) => msg.sender === "assistant" && msg.tool_call_id);

    const isInterruptionResponse = !!lastAssistantMsg;

    const userMessage: Message = {
      id: Date.now().toString(),
      content: inputValue,
      sender: "user",
      timestamp: new Date().toISOString(),
      type: "text",
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue("");
    setIsLoading(true);

    // Get user id from localStorage (adjust if your user object is stored differently)
    const user = localStorage.getItem("user")
      ? JSON.parse(localStorage.getItem("user") || "{}")
      : {};
    const userId = user.id || localStorage.getItem("user_id") || "";

    const payload = {
      message: userMessage.content,
      is_interruption_response: isInterruptionResponse,
    };
    console.log("Sending message:", payload);
    fetch(`http://localhost:8000/chats/${sessionId}/send_message`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-User-ID": userId,
      },
      body: JSON.stringify(payload),
    })
      .then((res) => {
        if (!res.ok) {
          return res.json().then((err) => {
            throw new Error(err.detail || "Failed to send message");
          });
        }
        return res.json();
      })
      .then((data) => {
        if (data && data.bot_response) {
          const aiResponse: Message = {
            id: (Date.now() + 1).toString(),
            content: data.bot_response,
            sender: "assistant",
            timestamp: new Date().toISOString(),
            type: "text",
            ...(data.updated_chat_history &&
              Array.isArray(data.updated_chat_history) &&
              data.updated_chat_history.length > 0 &&
              data.updated_chat_history[data.updated_chat_history.length - 1]
                .tool_call_id && {
                tool_call_id:
                  data.updated_chat_history[
                    data.updated_chat_history.length - 1
                  ].tool_call_id,
              }),
          };
          setMessages((prev) => [...prev, aiResponse]);
        }
      })
      .catch((err) => {
        // Optionally show error to user
        console.error("Send message error:", err);
      })
      .finally(() => setIsLoading(false));
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <Card className="h-[calc(100vh-200px)] flex flex-col">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2">
          <Bot className="h-5 w-5 text-blue-600" />
          Tax Advisor Chat
          {sessionId && <Badge variant="secondary">Session {sessionId}</Badge>}
        </CardTitle>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col p-0 min-h-0">
        <ScrollArea className="flex-1 px-4 min-h-0">
          <div className="space-y-4 pb-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex items-start gap-3 ${
                  message.sender === "user" ? "flex-row-reverse" : ""
                }`}
              >
                <Avatar className="h-8 w-8 flex-shrink-0">
                  <AvatarFallback
                    className={
                      message.sender === "assistant"
                        ? "bg-blue-100 text-blue-600"
                        : "bg-green-100 text-green-600"
                    }
                  >
                    {message.sender === "assistant" ? (
                      <Bot className="h-4 w-4" />
                    ) : (
                      <User className="h-4 w-4" />
                    )}
                  </AvatarFallback>
                </Avatar>

                <div
                  className={`max-w-[80%] ${
                    message.sender === "user" ? "text-right" : ""
                  }`}
                >
                  <div
                    className={`rounded-lg px-4 py-2 ${
                      message.sender === "assistant"
                        ? "bg-white text-black"
                        : "bg-blue-600 text-white"
                    }`}
                  >
                    <div
                      className="whitespace-pre-wrap text-sm text-left"
                      dangerouslySetInnerHTML={{
                        __html: formatContent(message.content),
                      }}
                    />
                  </div>
                  <div className="text-xs text-muted-foreground mt-1">
                    {new Date(message.timestamp).toLocaleTimeString()}
                  </div>
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="flex items-start gap-3">
                <Avatar className="h-8 w-8 flex-shrink-0">
                  <AvatarFallback className="bg-blue-100 text-blue-600">
                    <Bot className="h-4 w-4" />
                  </AvatarFallback>
                </Avatar>
                <div className="bg-gray-100 rounded-lg px-4 py-2">
                  <div className="flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span className="text-sm text-gray-600">
                      AI is thinking...
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
          <div ref={messagesEndRef} />
        </ScrollArea>

        {/* Input section: fixed, not scrollable */}
        <div className="border-t p-4 bg-white sticky bottom-0">
          <div className="flex gap-2">
            <Input
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask about tax deductions, filing requirements, or get tax advice..."
              className="flex-1"
              disabled={isLoading}
            />
            <Button
              onClick={handleSendMessage}
              disabled={!inputValue.trim() || isLoading}
              size="icon"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>

          <div className="flex gap-2 mt-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                setInputValue("What deductions am I eligible for?")
              }
            >
              <FileText className="h-3 w-3 mr-1" />
              Deductions
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                setInputValue("How can I save on taxes this year?")
              }
            >
              Tax Savings
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                setInputValue("Help me with home office deduction")
              }
            >
              Home Office
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
