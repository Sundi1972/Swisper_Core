import React, { useState } from 'react';
import InputField from '../ui/InputField';

interface HeaderProps {
  onSearch?: (query: string) => void;
}

const Header: React.FC<HeaderProps> = ({
  onSearch = () => {},
}) => {
  const [searchQuery, setSearchQuery] = useState('');

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
    onSearch(e.target.value);
  };

  return (
    <header className="flex items-center justify-between p-4 bg-chat-background border-b border-chat-muted">
      <div className="flex items-center space-x-4">
        <div className="text-chat-text font-bold text-xl">Swisper</div>
      </div>

      <div className="flex-1 max-w-md mx-8">
        <InputField
          placeholder="Search conversations..."
          value={searchQuery}
          onChange={handleSearchChange}
          className="w-full"
        />
      </div>

      <div className="flex items-center space-x-4">
        <div className="h-8 w-8 bg-chat-accent rounded-full flex items-center justify-center">
          <span className="text-white text-sm font-medium">U</span>
        </div>
      </div>
    </header>
  );
};

export default Header;
