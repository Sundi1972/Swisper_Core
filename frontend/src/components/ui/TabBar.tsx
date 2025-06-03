import React from 'react';
import { Tab } from '../../types';

interface TabBarProps {
  tabs: Tab[];
  activeTab: string;
  onTabChange: (tabId: string) => void;
}

const TabBar: React.FC<TabBarProps> = ({ tabs, activeTab, onTabChange }) => {
  return (
    <div className="flex items-center border-b border-chat-muted mb-6">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onTabChange(tab.id)}
          className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
            activeTab === tab.id
              ? 'text-chat-accent border-chat-accent'
              : 'text-chat-secondary border-transparent hover:text-chat-text hover:border-chat-muted'
          }`}
        >
          <div className="flex items-center space-x-2">
            {tab.icon && (
              <img src={tab.icon} alt="" className="h-4 w-4" />
            )}
            <span>{tab.label}</span>
          </div>
        </button>
      ))}
    </div>
  );
};

export default TabBar;
