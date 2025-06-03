import React, { useState, useEffect } from 'react';
import { Button } from '../ui/Button';

interface Session {
  id: string;
  message_count: number;
  last_message: string;
  last_timestamp: string | null;
  has_contract: boolean;
}

interface SidebarProps {
  onSectionSelect?: (section: string) => void;
  onSessionSelect?: (sessionId: string) => void;
  currentSessionId?: string;
  isCollapsed?: boolean;
}

const Sidebar: React.FC<SidebarProps> = ({
  onSectionSelect = () => {},
  onSessionSelect = () => {},
  currentSessionId = '',
  isCollapsed = false,
}) => {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(false);
  const [expandedSections, setExpandedSections] = useState<{[key: string]: boolean}>({
    recent: true
  });

  const fetchSessions = async () => {
    try {
      setLoading(true);
      const response = await fetch('http://localhost:8000/api/sessions');
      const data = await response.json();
      
      const sessionArray = Object.values(data.sessions || {}) as Session[];
      sessionArray.sort((a, b) => {
        const timeA = a.last_timestamp ? new Date(a.last_timestamp).getTime() : 0;
        const timeB = b.last_timestamp ? new Date(b.last_timestamp).getTime() : 0;
        return timeB - timeA;
      });
      
      setSessions(sessionArray);
    } catch (error) {
      console.error('Error fetching sessions:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSessions();
  }, []);

  const toggleSection = (sectionId: string) => {
    setExpandedSections((prev) => ({
      ...prev,
      [sectionId]: !prev[sectionId]
    }));
  };

  const formatTimestamp = (timestamp: string | null) => {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  const createNewSession = () => {
    const newSessionId = `session_${Date.now()}`;
    onSessionSelect(newSessionId);
    fetchSessions();
  };

  if (isCollapsed) {
    return (
      <aside className="w-16 bg-chat-message rounded-lg p-2 h-full">
        <div className="flex flex-col items-center space-y-4">
          <div className="w-8 h-8 bg-chat-accent rounded-lg flex items-center justify-center">
            <span className="text-white text-sm">S</span>
          </div>
        </div>
      </aside>
    );
  }

  return (
    <aside className="w-64 bg-chat-message rounded-lg p-4 h-full overflow-y-auto">
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-chat-text text-sm font-medium uppercase tracking-wide">Recent Chats</h2>
          <Button
            variant="outline"
            size="icon"
            color="secondary"
            className="h-6 w-6"
            onClick={createNewSession}
            title="New Session"
          >
            +
          </Button>
        </div>

        {loading ? (
          <div className="text-chat-secondary text-sm">Loading sessions...</div>
        ) : (
          <div className="space-y-2">
            {sessions.length === 0 ? (
              <div className="text-chat-secondary text-sm">No sessions yet</div>
            ) : (
              sessions.map((session) => (
                <div 
                  key={session.id}
                  className={`cursor-pointer hover:bg-chat-background rounded-lg p-2 -mx-2 transition-colors ${
                    currentSessionId === session.id ? 'bg-chat-background border-l-2 border-chat-accent' : ''
                  }`}
                  onClick={() => onSessionSelect(session.id)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="text-chat-text text-sm font-medium truncate">
                        Session {session.id.slice(-8)}
                        {session.has_contract && (
                          <span className="ml-1 text-chat-accent">📄</span>
                        )}
                      </div>
                      {session.last_message && (
                        <div className="text-chat-secondary text-xs truncate mt-1">
                          {session.last_message}
                        </div>
                      )}
                      <div className="text-chat-muted text-xs mt-1">
                        {session.message_count} messages • {formatTimestamp(session.last_timestamp)}
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>

      <div className="mt-auto">
        <Button
          variant="outline"
          color="primary"
          className="w-full"
          size="xs"
          onClick={() => onSectionSelect('settings')}
        >
          Settings
        </Button>
      </div>
    </aside>
  );
};

export default Sidebar;
