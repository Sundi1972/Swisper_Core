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
}
