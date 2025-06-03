import React, { useState, useEffect } from 'react';
import { Button } from '../ui/Button';

interface Session {
  id: string;
  title?: string;
  last_user_message?: string;
  message_count: number;
  last_updated?: string;
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
    chats: true
  });

  const fetchSessions = async () => {
    try {
      setLoading(true);
      const response = await fetch('http://localhost:8000/api/sessions');
      const data = await response.json();
      
      const sessionArray = Object.values(data.sessions || {}) as Session[];
      sessionArray.sort((a, b) => {
        const timeA = a.last_updated ? new Date(a.last_updated).getTime() : 0;
        const timeB = b.last_updated ? new Date(b.last_updated).getTime() : 0;
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
      <aside className="w-16 bg-[#141923] rounded-2xl p-2 h-full">
        <div className="flex flex-col items-center space-y-4">
          <div className="w-8 h-8 bg-[#00a9dd] rounded-lg flex items-center justify-center">
            <span className="text-white text-sm">S</span>
          </div>
        </div>
      </aside>
    );
  }

  return (
    <aside className="w-[267px] bg-[#141923] rounded-2xl p-8 h-full overflow-y-auto">
      <div className="mb-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-[#f9fbfc] text-sm font-normal uppercase tracking-wide">CHATS</h2>
          <img 
            src="/images/img_addfilled.svg" 
            alt="Add" 
            className="h-5 w-5 cursor-pointer hover:opacity-80" 
            onClick={createNewSession}
          />
        </div>

        {loading ? (
          <div className="text-[#8f99ad] text-sm">Loading sessions...</div>
        ) : (
          <div className="space-y-4">
            {sessions.length === 0 ? (
              <div className="text-[#8f99ad] text-sm">No sessions yet</div>
            ) : (
              sessions.map((session) => (
                <div 
                  key={session.id}
                  className={`cursor-pointer hover:bg-[#222834] rounded-lg p-2 -mx-2 transition-colors ${
                    currentSessionId === session.id ? 'bg-[#222834] border-l-2 border-[#00a9dd]' : ''
                  }`}
                  onClick={() => onSessionSelect(session.id)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="text-[#f9fbfc] text-sm font-medium truncate">
                        {session.title || 'Untitled Session'}
                        {session.has_contract && (
                          <span className="ml-1 text-[#00a9dd]">📄</span>
                        )}
                      </div>
                      <div className="text-[#b6c2d1] text-xs truncate mt-1">
                        {session.last_user_message || 'No messages yet'}
                      </div>
                      <div className="text-[#8f99ad] text-xs mt-1">
                        {session.message_count} messages{session.last_updated ? ` • ${session.last_updated}` : ''}
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>

      <div className="mb-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-[#f9fbfc] text-sm font-normal uppercase tracking-wide">BOOKMARKS</h2>
          <img src="/images/img_addfilled.svg" alt="Add" className="h-5 w-5 cursor-pointer hover:opacity-80" />
        </div>

        <div className="space-y-4">
          {['Mental Health', 'Home Appliances', 'Education'].map((bookmark, index) => (
            <div
              key={index}
              className="text-[#f9fbfc] text-sm cursor-pointer hover:bg-[#222834] rounded-lg p-2 -mx-2 transition-colors"
              onClick={() => onSectionSelect(bookmark.toLowerCase().replace(' ', '-'))}
            >
              {bookmark}
            </div>
          ))}
        </div>
      </div>

      <div className="mb-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-[#f9fbfc] text-sm font-normal uppercase tracking-wide">NOTES</h2>
          <img src="/images/img_addfilled.svg" alt="Add" className="h-5 w-5 cursor-pointer hover:opacity-80" />
        </div>

        <div className="space-y-4">
          {['Air Conditioner', 'Mental Health', 'Home Appliances', 'Education'].map((note, index) => (
            <div key={index}>
              {index === 0 ? (
                <div className="flex items-center space-x-3 cursor-pointer hover:bg-[#222834] rounded-lg p-2 -mx-2 transition-colors">
                  <img src="/images/img_folderfilled.svg" alt="" className="h-6 w-6" />
                  <span className="text-[#f9fbfc] text-sm">{note}</span>
                  <img src="/images/img_expandlessfilled.svg" alt="Toggle" className="h-6 w-6 ml-auto" />
                </div>
              ) : (
                <div
                  className="text-[#f9fbfc] text-sm cursor-pointer hover:bg-[#222834] rounded-lg p-2 -mx-2 transition-colors"
                  onClick={() => onSectionSelect(note.toLowerCase().replace(' ', '-'))}
                >
                  {note}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="mt-auto">
        <Button
          onClick={() => onSectionSelect('feedback')}
          variant="outline"
          color="primary"
          className="w-full border-[#00a9dd] text-[#00a9dd] rounded-[21px] h-[42px] hover:bg-[#00a9dd] hover:text-white transition-colors"
        >
          Feedback
        </Button>
      </div>
    </aside>
  );
};

export default Sidebar;
