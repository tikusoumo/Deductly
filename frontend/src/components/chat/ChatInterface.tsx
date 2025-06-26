import React, { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Send, Bot, User, FileText, Loader2 } from 'lucide-react';
import { Message } from '@/types';
import { Badge } from '@/components/ui/badge';

interface ChatInterfaceProps {
  sessionId?: string;
  onNewSession?: () => void;
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({ sessionId, onNewSession }) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      content: 'Hello! I\'m your AI tax advisor. I can help you find tax deductions, answer questions about tax laws, and guide you through the tax filing process. What would you like to know?',
      sender: 'ai',
      timestamp: new Date().toISOString(),
      type: 'text'
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      content: inputValue,
      sender: 'user',
      timestamp: new Date().toISOString(),
      type: 'text'
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    // Simulate AI response
    setTimeout(() => {
      const aiResponse: Message = {
        id: (Date.now() + 1).toString(),
        content: generateAIResponse(inputValue),
        sender: 'ai',
        timestamp: new Date().toISOString(),
        type: 'text'
      };
      setMessages(prev => [...prev, aiResponse]);
      setIsLoading(false);
    }, 1000);
  };

  const generateAIResponse = (userInput: string): string => {
    const lowerInput = userInput.toLowerCase();
    
    if (lowerInput.includes('deduction') || lowerInput.includes('tax saving')) {
      return 'Here are some common tax deductions you might be eligible for:\n\n• Home office expenses\n• Professional development costs\n• Charitable donations\n• Medical expenses\n• Business travel expenses\n\nWould you like me to help you calculate potential savings for any of these?';
    }
    
    if (lowerInput.includes('home office')) {
      return 'For home office deductions, you can choose between:\n\n1. **Simplified method**: $5 per square foot (up to 300 sq ft)\n2. **Actual expense method**: Percentage of home expenses\n\nWhat\'s the square footage of your home office?';
    }
    
    if (lowerInput.includes('medical')) {
      return 'Medical expenses are deductible if they exceed 7.5% of your adjusted gross income. This includes:\n\n• Doctor visits and treatments\n• Prescription medications\n• Medical equipment\n• Health insurance premiums (in some cases)\n\nDo you have medical expenses you\'d like to calculate?';
    }
    
    return 'I understand you\'re asking about tax matters. Could you provide more specific details about your situation? For example:\n\n• What type of deductions are you interested in?\n• Are you filing as an individual or business?\n• What tax year are you planning for?\n\nThis will help me give you more targeted advice.';
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
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
      
      <CardContent className="flex-1 flex flex-col p-0">
        <ScrollArea className="flex-1 px-4">
          <div className="space-y-4 pb-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex items-start gap-3 ${
                  message.sender === 'user' ? 'flex-row-reverse' : ''
                }`}
              >
                <Avatar className="h-8 w-8 flex-shrink-0">
                  <AvatarFallback className={
                    message.sender === 'ai' 
                      ? 'bg-blue-100 text-blue-600' 
                      : 'bg-green-100 text-green-600'
                  }>
                    {message.sender === 'ai' ? <Bot className="h-4 w-4" /> : <User className="h-4 w-4" />}
                  </AvatarFallback>
                </Avatar>
                
                <div className={`max-w-[80%] ${message.sender === 'user' ? 'text-right' : ''}`}>
                  <div className={`rounded-lg px-4 py-2 ${
                    message.sender === 'ai'
                      ? 'bg-gray-100 text-gray-900'
                      : 'bg-blue-600 text-white'
                  }`}>
                    <div className="whitespace-pre-wrap text-sm">
                      {message.content}
                    </div>
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
                    <span className="text-sm text-gray-600">AI is thinking...</span>
                  </div>
                </div>
              </div>
            )}
          </div>
          <div ref={messagesEndRef} />
        </ScrollArea>
        
        <div className="border-t p-4">
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
            <Button variant="outline" size="sm" onClick={() => setInputValue("What deductions am I eligible for?")}>
              <FileText className="h-3 w-3 mr-1" />
              Deductions
            </Button>
            <Button variant="outline" size="sm" onClick={() => setInputValue("How can I save on taxes this year?")}>
              Tax Savings
            </Button>
            <Button variant="outline" size="sm" onClick={() => setInputValue("Help me with home office deduction")}>
              Home Office
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};