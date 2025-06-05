import React, { useState } from 'react';

import InputField from '../ui/InputField';

interface HeaderProps {
  onSearch?: (query: string) => void;
  isFullWidth?: boolean;
  onToggleFullWidth?: () => void;
}

const Header: React.FC<HeaderProps> = ({
  onSearch = () => {},
  isFullWidth = false,
  onToggleFullWidth = () => {},
}) => {
  const [searchQuery, setSearchQuery] = useState('');

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
    onSearch(e.target.value);
  };

  return (
    <header className="flex items-center justify-between p-4 bg-[#020305]">
      <div className="flex items-center space-x-4">
        <img src="/images/img_group_4.svg" alt="Swiper Logo" className="h-8 w-9" />
        <img src="/images/img_group_3.svg" alt="Swiper Text" className="h-7 w-26" />
      </div>

      <div className="flex-1 max-w-md mx-8">
        <div className="relative flex items-center bg-transparent border border-[#8f99ad] rounded-[20px] px-3 py-2">
          <img src="/images/img_searchfilled.svg" alt="Search" className="h-6 w-6 mr-3" />
          <InputField
            placeholder="Search"
            value={searchQuery}
            onChange={handleSearchChange}
            className="border-none bg-transparent text-[#f9fbfc] placeholder-[#f9fbfc] focus:border-none"
          />
          <img src="/images/img_filterlistfilled.svg" alt="Filter" className="h-6 w-6 ml-3 cursor-pointer" />
        </div>
      </div>

      <div className="flex items-center space-x-4">
        <span className="text-[#b6c2d1] text-sm">Full Width</span>
        <button onClick={onToggleFullWidth} className="relative">
          <img src="/images/img_switch.svg" alt="Toggle" className="h-[38px] w-[58px]" />
        </button>
        <img src="/images/img_icon_blue_gray_200.svg" alt="Icon" className="h-6 w-6 cursor-pointer" />
        <img src="/images/img_morevertfilled.svg" alt="More" className="h-6 w-6 cursor-pointer" />
        <img src="/images/img_avatar.png" alt="Avatar 1" className="h-10 w-10 rounded-full" />
        <div className="relative">
          <img src="/images/img_.png" alt="Avatar 2" className="h-10 w-10 rounded-full" />
          <div className="absolute bottom-0 right-0 h-3 w-3 bg-white rounded-full flex items-center justify-center">
            <div className="h-2 w-2 bg-[#2e7d32] rounded-full"></div>
          </div>
        </div>
        <img src="/images/img_avatar_40x40.png" alt="Avatar 3" className="h-10 w-10 rounded-full" />
        <div className="relative">
          <img src="/images/img_avatar_1.png" alt="Avatar 4" className="h-10 w-10 rounded-full border-3 border-[#00a9dd]" />
        </div>
      </div>
    </header>
  );
};

export default Header;