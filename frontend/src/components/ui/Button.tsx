import React from 'react';
import { ButtonProps } from '../../types';

const Button: React.FC<ButtonProps> = ({
  variant = 'fill',
  color = 'primary',
  size = 'sm',
  className = '',
  disabled = false,
  children,
  onClick = () => {},
  title,
}) => {
  const baseClasses = 'font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2';
  
  const variantClasses = {
    fill: {
      primary: 'bg-chat-accent text-white hover:bg-chat-accent/80 focus:ring-chat-accent',
      secondary: 'bg-chat-muted text-chat-text hover:bg-chat-muted/80 focus:ring-chat-muted',
    },
    outline: {
      primary: 'border border-chat-accent text-chat-accent hover:bg-chat-accent hover:text-white focus:ring-chat-accent',
      secondary: 'border border-chat-muted text-chat-secondary hover:bg-chat-muted hover:text-chat-text focus:ring-chat-muted',
    },
  };

  const sizeClasses = {
    xs: 'px-3 py-1.5 text-xs',
    sm: 'px-4 py-2 text-sm',
    icon: 'p-2',
  };

  const disabledClasses = disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer';

  const buttonClasses = `${baseClasses} ${variantClasses[variant][color]} ${sizeClasses[size]} ${disabledClasses} ${className}`;

  return (
    <button
      className={buttonClasses}
      onClick={onClick}
      disabled={disabled}
      title={title}
    >
      {children}
    </button>
  );
};

export { Button };
