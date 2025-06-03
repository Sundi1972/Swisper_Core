import React, { useState, useEffect } from 'react';
import InputField from '../ui/InputField';

interface SearchResult {
  session_id: string;
  message_index: number;
  role: string;
  content: string;
  timestamp: string | null;
  preview: string;
}

interface HeaderProps {
  onSearch?: (query: string) => void;
  onSearchResultSelect?: (sessionId: string, messageIndex: number) => void;
}

const Header: React.FC<HeaderProps> = ({
  onSearch = () => {},
  onSearchResultSelect = () => {},
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [showResults, setShowResults] = useState(false);
  const [searching, setSearching] = useState(false);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const query = e.target.value;
    setSearchQuery(query);
    onSearch(query);
    
    if (query.trim().length > 2) {
      performSearch(query);
    } else {
      setSearchResults([]);
      setShowResults(false);
    }
  };

  const performSearch = async (query: string) => {
    try {
      setSearching(true);
      const response = await fetch(`http://localhost:8000/api/search?query=${encodeURIComponent(query)}`);
      const data = await response.json();
      
      setSearchResults(data.results || []);
      setShowResults(true);
    } catch (error) {
      console.error('Error searching:', error);
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  };

  const handleResultClick = (result: SearchResult) => {
    onSearchResultSelect(result.session_id, result.message_index);
    setShowResults(false);
    setSearchQuery('');
  };

  const handleClickOutside = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      setShowResults(false);
    }
  };

  return (
    <header className="flex items-center justify-between p-4 bg-chat-background border-b border-chat-muted relative">
      <div className="flex items-center space-x-4">
        <div className="text-chat-text font-bold text-xl">Swisper</div>
      </div>

      <div className="flex-1 max-w-md mx-8 relative">
        <InputField
          placeholder="Search conversations..."
          value={searchQuery}
          onChange={handleSearchChange}
          className="w-full"
        />
        
        {showResults && (
          <div className="absolute top-full left-0 right-0 mt-1 bg-chat-message border border-chat-muted rounded-lg shadow-lg z-50 max-h-96 overflow-y-auto">
            {searching ? (
              <div className="p-4 text-chat-secondary text-sm">Searching...</div>
            ) : searchResults.length === 0 ? (
              <div className="p-4 text-chat-secondary text-sm">No results found</div>
            ) : (
              <div className="py-2">
                {searchResults.slice(0, 10).map((result, index) => (
                  <div
                    key={`${result.session_id}-${result.message_index}`}
                    className="px-4 py-2 hover:bg-chat-background cursor-pointer border-b border-chat-muted last:border-b-0"
                    onClick={() => handleResultClick(result)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="text-chat-text text-sm font-medium">
                          Session {result.session_id.slice(-8)} • {result.role}
                        </div>
                        <div className="text-chat-secondary text-xs truncate mt-1">
                          {result.preview}
                        </div>
                        {result.timestamp && (
                          <div className="text-chat-muted text-xs mt-1">
                            {new Date(result.timestamp).toLocaleString()}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
                {searchResults.length > 10 && (
                  <div className="px-4 py-2 text-chat-secondary text-xs text-center">
                    Showing first 10 of {searchResults.length} results
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      <div className="flex items-center space-x-4">
        <div className="h-8 w-8 bg-chat-accent rounded-full flex items-center justify-center">
          <span className="text-white text-sm font-medium">U</span>
        </div>
      </div>
      
      {showResults && (
        <div 
          className="fixed inset-0 z-40" 
          onClick={handleClickOutside}
        />
      )}
    </header>
  );
};

export default Header;
