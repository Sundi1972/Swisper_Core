import React, { useState } from 'react';
import { Button } from '../ui/Button';

interface SidebarProps {
  onSectionSelect?: (section: string) => void;
  isCollapsed?: boolean;
}

const Sidebar: React.FC<SidebarProps> = ({
  onSectionSelect = () => {},
  isCollapsed = false,
}) => {
  const [expandedSections, setExpandedSections] = useState<{[key: string]: boolean}>({
    recent: true
  });

  const toggleSection = (sectionId: string) => {
    setExpandedSections((prev) => ({
      ...prev,
      [sectionId]: !prev[sectionId]
    }));
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
          >
            +
          </Button>
        </div>

        <div className="space-y-2">
          <div 
            className="text-chat-text text-sm cursor-pointer hover:bg-chat-background rounded-lg p-2 -mx-2"
            onClick={() => onSectionSelect('current-session')}
          >
            Current Session
          </div>
          <div 
            className="text-chat-secondary text-sm cursor-pointer hover:bg-chat-background rounded-lg p-2 -mx-2"
            onClick={() => onSectionSelect('previous-session')}
          >
            Previous Session
          </div>
        </div>
      </div>

      <div className="mt-auto">
        <Button
          variant="outline"
          color="primary"
          className="w-full"
          size="xs"
        >
          Settings
        </Button>
      </div>
    </aside>
  );
};

export default Sidebar;
