import React, { useState } from 'react';
import { ChatInterface } from '@/components/chat/ChatInterface';
import { ChatSessions } from '@/components/chat/ChatSessions';

export const Chat: React.FC = () => {
  const [selectedSessionId, setSelectedSessionId] = useState<string | undefined>();

  const handleSelectSession = (sessionId: string) => {
    setSelectedSessionId(sessionId);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Tax Consultations</h1>
          <p className="text-gray-600 mt-1">Chat with our AI tax advisor for personalized guidance.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-1 ">
        {/* <div className="lg:col-span-1">
          <ChatSessions 
            onSelectSession={handleSelectSession}
            selectedSessionId={selectedSessionId}
          />
        </div> */}
        <div className="lg:col-span-2">
          <ChatInterface 
            sessionId={selectedSessionId}
            onNewSession={() => setSelectedSessionId(undefined)}
          />
        </div>
      </div>
    </div>
  );
};