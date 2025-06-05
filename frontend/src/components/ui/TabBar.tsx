import React from 'react';
import { Tab } from '../../types';

interface TabBarProps {
  tabs: Tab[];
  activeTab: string;
  onTabChange: (tabId: string) => void;
}

const TabBar: React.FC<TabBarProps> = ({ tabs, activeTab, onTabChange }) => {
  return (
    <div className="flex border-b border-[#8f99ad]">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onTabChange(tab.id)}
          className={`flex items-center space-x-2 px-6 py-3 font-medium text-sm border-b-2 transition-colors ${
            activeTab === tab.id
              ? 'border-[#00a9dd] text-[#00a9dd]'
              : 'border-transparent text-[#b6c2d1] hover:text-[#f9fbfc]'
          }`}
        >
          {tab.icon && (
            <svg className="h-5 w-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
          )}
          <span>{tab.label}</span>
        </button>
      ))}
    </div>
  );
};

export default TabBar;
