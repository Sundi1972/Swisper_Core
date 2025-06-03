export interface Tab {
  id: string;
  label: string;
  icon?: string;
}

export interface ButtonProps {
  variant?: 'fill' | 'outline';
  color?: 'primary' | 'secondary';
  size?: 'xs' | 'sm' | 'icon';
  className?: string;
  disabled?: boolean;
  children: React.ReactNode;
  onClick?: () => void;
  title?: string;
}

export interface Message {
  id: string;
  content: string;
  timestamp: string;
  isUser: boolean;
}

export interface Session {
  id: string;
  message_count: number;
  last_message: string;
  last_timestamp: string | null;
  has_contract: boolean;
}
