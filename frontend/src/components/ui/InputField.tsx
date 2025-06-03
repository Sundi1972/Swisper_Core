import React from 'react';

interface InputFieldProps {
  placeholder?: string;
  value?: string;
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onKeyPress?: (e: React.KeyboardEvent<HTMLInputElement>) => void;
  className?: string;
  type?: string;
  disabled?: boolean;
}

const InputField: React.FC<InputFieldProps> = ({
  placeholder = "",
  value = "",
  onChange = () => {},
  onKeyPress = () => {},
  className = "",
  type = "text",
  disabled = false,
}) => {
  return (
    <input
      type={type}
      placeholder={placeholder}
      value={value}
      onChange={onChange}
      onKeyPress={onKeyPress}
      disabled={disabled}
      className={`w-full px-4 py-2 bg-transparent border border-chat-muted rounded-lg text-chat-text placeholder-chat-muted focus:outline-none focus:border-chat-accent transition-colors ${className}`}
    />
  );
};

export default InputField;
