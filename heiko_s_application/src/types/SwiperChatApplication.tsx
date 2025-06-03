// src/types/SwiperChatApplication.tsx
export interface Message {
  id: string;
  content: string;
  timestamp: string;
  isUser: boolean;
}

export interface ChatSection {
  id: string;
  name: string;
  icon?: string;
  isExpanded?: boolean;
  children?: ChatSection[];
}

export interface User {
  id: string;
  name: string;
  avatar: string;
  isOnline: boolean;
}

export interface Tab {
  id: string;
  label: string;
  icon?: string;
}

export interface SwiperChatApplicationProps {
  currentUser?: User;
  messages?: Message[];
  onSendMessage?: (message: string) => void;
  onVoiceInput?: () => void;
  onSearch?: (query: string) => void;
}

export interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  onVoiceInput: () => void;
  onAddAction: () => void;
  onNewSession: () => void;
  onAskDox: () => void;
  placeholder?: string;
}

export interface MessageBubbleProps {
  message: Message;
  isUser: boolean;
}