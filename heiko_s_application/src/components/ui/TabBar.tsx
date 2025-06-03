// src/components/ui/TabBar.tsx
import React from 'react';

interface Tab {
  id: string;
  label: string;
  icon?: string;
}

interface TabBarProps {
  tabs: Tab[];
  activeTab: string;
  onTabChange: (tabId: string) => void;
}

const TabBar: React.FC<TabBarProps> = ({ tabs, activeTab, onTabChange }) => {
  return (
    <div className="flex items-center border-b border-[#222834] mb-6">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onTabChange(tab.id)}
          className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
            activeTab === tab.id
              ? 'text-[#00a9dd] border-[#00a9dd]'
              : 'text-[#8f99ad] border-transparent hover:text-[#f9fbfc] hover:border-[#8f99ad]'
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