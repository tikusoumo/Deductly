import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ChatSession } from '@/types';
import { MessageCircle, Plus, Clock, CheckCircle, Archive } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

interface ChatSessionsProps {
  onSelectSession: (sessionId: string) => void;
  selectedSessionId?: string;
}

export const ChatSessions: React.FC<ChatSessionsProps> = ({ onSelectSession, selectedSessionId }) => {
  const [sessions, setSessions] = useState<ChatSession[]>([]);

  useEffect(() => {
    // Mock data - replace with actual API call
    const mockSessions: ChatSession[] = [
      {
        id: '1',
        title: 'Home Office Deductions',
        createdAt: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(),
        updatedAt: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
        messageCount: 12,
        status: 'active'
      },
      {
        id: '2',
        title: 'Medical Expense Calculations',
        createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(),
        updatedAt: new Date(Date.now() - 1000 * 60 * 60 * 4).toISOString(),
        messageCount: 8,
        status: 'completed'
      },
      {
        id: '3',
        title: 'Business Travel Expenses',
        createdAt: new Date(Date.now() - 1000 * 60 * 60 * 48).toISOString(),
        updatedAt: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(),
        messageCount: 15,
        status: 'active'
      },
      {
        id: '4',
        title: 'Charitable Donations Guide',
        createdAt: new Date(Date.now() - 1000 * 60 * 60 * 72).toISOString(),
        updatedAt: new Date(Date.now() - 1000 * 60 * 60 * 48).toISOString(),
        messageCount: 6,
        status: 'archived'
      }
    ];
    setSessions(mockSessions);
  }, []);

  const getStatusIcon = (status: ChatSession['status']) => {
    switch (status) {
      case 'active':
        return <Clock className="h-4 w-4" />;
      case 'completed':
        return <CheckCircle className="h-4 w-4" />;
      case 'archived':
        return <Archive className="h-4 w-4" />;
    }
  };

  const getStatusColor = (status: ChatSession['status']) => {
    switch (status) {
      case 'active':
        return 'bg-blue-100 text-blue-800';
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'archived':
        return 'bg-gray-100 text-gray-800';
    }
  };

  const startNewSession = async () => {
    // Mock new session creation
    const newSession: ChatSession = {
      id: (Date.now()).toString(),
      title: 'New Tax Consultation',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      messageCount: 0,
      status: 'active'
    };
    
    setSessions(prev => [newSession, ...prev]);
    onSelectSession(newSession.id);
  };

  return (
    <>
    <Card className="h-[calc(100vh-200px)]">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <MessageCircle className="h-5 w-5" />
            Chat Sessions
          </CardTitle>
          <Button onClick={startNewSession} size="sm">
            <Plus className="h-4 w-4 mr-1" />
            New Chat
          </Button>
        </div>
      </CardHeader>
      
      <CardContent className="p-0">
        <ScrollArea className="h-[calc(100vh-300px)]">
          <div className="space-y-2 p-4">
            {sessions.map((session) => (
              <div
                key={session.id}
                className={`p-4 rounded-lg border cursor-pointer transition-colors hover:bg-gray-50 ${
                  selectedSessionId === session.id ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                }`}
                onClick={() => onSelectSession(session.id)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium text-sm truncate">
                      {session.title}
                    </h3>
                    <div className="flex items-center gap-2 mt-1">
                      <Badge variant="secondary" className={`text-xs ${getStatusColor(session.status)}`}>
                        {getStatusIcon(session.status)}
                        <span className="ml-1 capitalize">{session.status}</span>
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        {session.messageCount} messages
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {formatDistanceToNow(new Date(session.updatedAt), { addSuffix: true })}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
    </>
  );
};