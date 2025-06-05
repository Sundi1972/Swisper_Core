import React from 'react';

interface InputFieldProps {
  placeholder?: string;
  value?: string;
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
  className?: string;
  type?: string;
  disabled?: boolean;
}

const InputField: React.FC<InputFieldProps> = ({
  placeholder = "",
  value = "",
  onChange = () => {},
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
      disabled={disabled}
      className={`w-full px-4 py-2 bg-transparent border border-[#8f99ad] rounded-lg text-[#f9fbfc] placeholder-[#8f99ad] focus:outline-none focus:border-[#00a9dd] ${className}`}
    />
  );
};

export default InputField;