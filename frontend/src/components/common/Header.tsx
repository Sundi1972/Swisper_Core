import React, { useState } from 'react';
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
  isFullWidth?: boolean;
  onToggleFullWidth?: () => void;
  onToggleSidebar?: () => void;
  currentSessionId?: string | null;
}

const Header: React.FC<HeaderProps> = ({
  onSearch = () => {},
  onSearchResultSelect = () => {},
  isFullWidth = false,
  onToggleFullWidth = () => {},
  onToggleSidebar = () => {},
  currentSessionId = null,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [showResults, setShowResults] = useState(false);
  const [searching, setSearching] = useState(false);
  const [searchScope, setSearchScope] = useState<'current' | 'global'>('global');

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
      const sessionParam = searchScope === 'current' && currentSessionId 
        ? `&session_id=${encodeURIComponent(currentSessionId)}` 
        : '';
      const response = await fetch(`http://localhost:8000/api/search?query=${encodeURIComponent(query)}${sessionParam}`);
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
    <header className="flex items-center justify-between p-4 bg-[#020305] relative">
      <div className="flex items-center space-x-4">
        <button onClick={onToggleSidebar} className="lg:hidden">
          <svg className="h-6 w-6 text-[#f9fbfc]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
        <div className="flex items-center space-x-3">
          <img src="/swisper-logo.png" alt="Swisper Logo" className="h-8 w-8" />
          <img src="/swisper-text.png" alt="Swisper" className="h-6 w-auto" />
        </div>
      </div>

      <div className="flex-1 max-w-md mx-8 relative">
        <div className="relative flex items-center bg-transparent border border-[#8f99ad] rounded-[20px] px-3 py-2">
          <svg className="h-6 w-6 mr-3 text-[#8f99ad]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <InputField
            placeholder="Search"
            value={searchQuery}
            onChange={handleSearchChange}
            className="border-none bg-transparent text-[#f9fbfc] placeholder-[#f9fbfc] focus:border-none"
          />
          
          <div className="flex items-center ml-3 space-x-2">
            <span className="text-[#8f99ad] text-xs whitespace-nowrap">
              {searchScope === 'current' ? 'Current Chat' : 'All Chats'}
            </span>
            <button 
              onClick={() => setSearchScope(searchScope === 'current' ? 'global' : 'current')}
              className="relative"
              disabled={searchScope === 'current' && !currentSessionId}
            >
              <div className={`w-[40px] h-[20px] rounded-full border transition-colors ${searchScope === 'current' ? 'bg-[#00a9dd] border-[#00a9dd]' : 'bg-transparent border-[#8f99ad]'}`}>
                <div className={`w-[16px] h-[16px] bg-white rounded-full transition-transform ${searchScope === 'current' ? 'translate-x-[22px]' : 'translate-x-[2px]'} mt-[2px]`}></div>
              </div>
            </button>
          </div>
        </div>
        
        {showResults && (
          <div className="absolute top-full left-0 right-0 mt-1 bg-[#141923] border border-[#8f99ad] rounded-lg shadow-lg z-50 max-h-96 overflow-y-auto">
            {searching ? (
              <div className="p-4 text-[#8f99ad] text-sm">Searching...</div>
            ) : searchResults.length === 0 ? (
              <div className="p-4 text-[#8f99ad] text-sm">No results found</div>
            ) : (
              <div className="py-2">
                {searchResults.slice(0, 10).map((result, index) => (
                  <div
                    key={`${result.session_id}-${result.message_index}`}
                    className="px-4 py-2 hover:bg-[#222834] cursor-pointer border-b border-[#8f99ad] last:border-b-0"
                    onClick={() => handleResultClick(result)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="text-[#f9fbfc] text-sm font-medium">
                          Session {result.session_id.slice(-8)} • {result.role}
                        </div>
                        <div className="text-[#b6c2d1] text-xs truncate mt-1">
                          {result.preview}
                        </div>
                        {result.timestamp && (
                          <div className="text-[#8f99ad] text-xs mt-1">
                            {new Date(result.timestamp).toLocaleString()}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
                {searchResults.length > 10 && (
                  <div className="px-4 py-2 text-[#b6c2d1] text-xs text-center">
                    Showing first 10 of {searchResults.length} results
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      <div className="flex items-center space-x-4">
        <span className="text-[#b6c2d1] text-sm">Full Width</span>
        <button onClick={onToggleFullWidth} className="relative">
          <div className={`w-[58px] h-[38px] rounded-full border-2 transition-colors ${isFullWidth ? 'bg-[#00a9dd] border-[#00a9dd]' : 'bg-transparent border-[#8f99ad]'}`}>
            <div className={`w-[30px] h-[30px] bg-white rounded-full transition-transform ${isFullWidth ? 'translate-x-[24px]' : 'translate-x-[2px]'} mt-[2px]`}></div>
          </div>
        </button>
        <img src="/pause-icon.png" alt="Pause" className="h-6 w-6 cursor-pointer" />
        <svg className="h-6 w-6 cursor-pointer text-[#8f99ad]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
        </svg>
        <div className="h-10 w-10 bg-[#8f99ad] rounded-full flex items-center justify-center">
          <span className="text-white text-sm font-medium">A1</span>
        </div>
        <div className="relative">
          <div className="h-10 w-10 bg-[#b6c2d1] rounded-full flex items-center justify-center">
            <span className="text-[#020305] text-sm font-medium">A2</span>
          </div>
          <div className="absolute bottom-0 right-0 h-3 w-3 bg-white rounded-full flex items-center justify-center">
            <div className="h-2 w-2 bg-[#2e7d32] rounded-full"></div>
          </div>
        </div>
        <div className="h-10 w-10 bg-[#8f99ad] rounded-full flex items-center justify-center">
          <span className="text-white text-sm font-medium">A3</span>
        </div>
        <div className="relative">
          <div className="h-10 w-10 bg-[#00a9dd] rounded-full flex items-center justify-center border-2 border-[#00a9dd]">
            <span className="text-white text-sm font-medium">A4</span>
          </div>
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
