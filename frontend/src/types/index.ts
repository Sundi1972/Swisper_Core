export interface Message {
  id: string;
  content: string;
  timestamp: string;
  isUser: boolean;
}

export interface Tab {
  id: string;
  label: string;
  icon?: string;
}

export interface User {
  id: string;
  name: string;
  avatar: string;
  isOnline: boolean;
}

export interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  onVoiceInput: () => void;
  onAddAction: () => void;
  onNewSession: () => void;
  onAskDocs: () => void;
  placeholder?: string;
}

export interface MessageBubbleProps {
  message: Message;
  isUser: boolean;
}
