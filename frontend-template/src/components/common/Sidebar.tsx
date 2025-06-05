import React, { useState } from 'react';
import { Button } from '../ui/Button';
import { ChatSection } from '../../types/SwiperChatApplication';

interface SidebarProps {
  onSectionSelect?: (section: string) => void;
  onFeedback?: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({
  onSectionSelect = () => {},
  onFeedback = () => {}, key
}) => {
  const [expandedSections, setExpandedSections] = useState<{[key: string]: boolean;}>({
    workout: true
  });

  const toggleSection = (sectionId: string) => {
    setExpandedSections((prev) => ({
      ...prev,
      [sectionId]: !prev[sectionId]
    }));
  };

  const chatSections: ChatSection[] = [
  {
    id: 'air-conditioner',
    name: 'Air Conditioner',
    icon: '/images/img_icon.svg'
  },
  {
    id: 'workout',
    name: 'Workout',
    icon: '/images/img_folderfilled.svg',
    isExpanded: expandedSections.workout,
    children: [
    { id: 'morning-routine', name: 'Morning routine' },
    { id: 'protein-intake', name: 'Protein intake' },
    { id: 'post-workout', name: 'Post workout routine' },
    { id: 'stretching', name: 'Stretching' }]

  },
  {
    id: 'air-conditioner-2',
    name: 'Air Conditioner',
    icon: '/images/img_folderfilled.svg'
  },
  {
    id: 'jiu-jitsu',
    name: 'Jiu-jitsu',
    icon: '/images/img_folderfilled.svg'
  },
  {
    id: 'meals',
    name: 'Meals',
    icon: '/images/img_folderfilled.svg'
  }];


  const bookmarkSections = [
  'Mental Health',
  'Home Appliances',
  'Education'];


  const notesSections = [
  {
    id: 'air-conditioner-notes',
    name: 'Air Conditioner',
    icon: '/images/img_folderfilled.svg'
  },
  'Mental Health',
  'Home Appliances',
  'Education'];


  return (
    <aside className="w-[267px] bg-[#141923] rounded-2xl p-8 h-full overflow-y-auto">
      {/* Chats Section */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-[#f9fbfc] text-sm font-normal uppercase tracking-wide">CHATS</h2>
          <img src="/images/img_addfilled.svg" alt="Add" className="h-5 w-5 cursor-pointer" />
        </div>

        <div className="space-y-4">
          {chatSections.map((section) =>
          <div key={section.id}>
              <div
              className="flex items-center justify-between cursor-pointer hover:bg-[#222834] rounded-lg p-2 -mx-2"
              onClick={() => {
                if (section.children) {
                  toggleSection(section.id);
                }
                onSectionSelect(section.id);
              }}>

                <div className="flex items-center space-x-3">
                  {section.icon &&
                <img src={section.icon} alt="" className="h-6 w-6" />
                }
                  <span className="text-[#f9fbfc] text-sm">{section.name}</span>
                </div>
                {section.children &&
              <img
                src={section.isExpanded ? "/images/img_expandlessfilled.svg" : "/images/img_icon.svg"}
                alt="Toggle"
                className="h-6 w-6" />

              }
              </div>

              {section.children && section.isExpanded &&
            <div className="ml-10 mt-2 space-y-2">
                  {section.children.map((child) =>
              <div
                key={child.id}
                className="text-[#f9fbfc] text-sm cursor-pointer hover:text-[#00a9dd] py-1"
                onClick={() => onSectionSelect(child.id)}>

                      {child.name}
                    </div>
              )}
                </div>
            }
            </div>
          )}
        </div>
      </div>

      {/* Bookmarks Section */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-[#f9fbfc] text-sm font-normal uppercase tracking-wide">BOOKMARKS</h2>
          <img src="/images/img_addfilled.svg" alt="Add" className="h-5 w-5 cursor-pointer" />
        </div>

        <div className="space-y-4">
          {bookmarkSections.map((bookmark, index) =>
          <div
            key={index}
            className="text-[#f9fbfc] text-sm cursor-pointer hover:bg-[#222834] rounded-lg p-2 -mx-2"
            onClick={() => onSectionSelect(bookmark.toLowerCase().replace(' ', '-'))}>

              {bookmark}
            </div>
          )}
        </div>
      </div>

      {/* Notes Section */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-[#f9fbfc] text-sm font-normal uppercase tracking-wide">NOTES</h2>
          <img src="/images/img_addfilled.svg" alt="Add" className="h-5 w-5 cursor-pointer" />
        </div>

        <div className="space-y-4">
          {notesSections.map((note, index) =>
          <div key={index}>
              {typeof note === 'object' ?
            <div className="flex items-center space-x-3 cursor-pointer hover:bg-[#222834] rounded-lg p-2 -mx-2">
                  <img src={note.icon} alt="" className="h-6 w-6" />
                  <span className="text-[#f9fbfc] text-sm">{note.name}</span>
                  <img src="/images/img_icon.svg" alt="Toggle" className="h-6 w-6 ml-auto" />
                </div> :

            <div
              className="text-[#f9fbfc] text-sm cursor-pointer hover:bg-[#222834] rounded-lg p-2 -mx-2"
              onClick={() => onSectionSelect(note.toLowerCase().replace(' ', '-'))}>

                  {note}
                </div>
            }
            </div>
          )}
        </div>
      </div>

      {/* Feedback Button */}
      <div className="mt-auto">
        <Button
          onClick={onFeedback}
          variant="outline"
          color="primary"
          className="w-full border-[#00a9dd] text-[#00a9dd] rounded-[21px] h-[42px]">

          Feedback
        </Button>
      </div>
    </aside>);

};

export default Sidebar;