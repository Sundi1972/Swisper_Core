import React from 'react';

const shapes = {
  round: "rounded-lg",
} as const;

const variants = {
  outline: {
    primary: "border-chat-accent border border-solid text-chat-accent hover:bg-chat-accent/10",
    secondary: "border-chat-muted border border-solid text-chat-secondary hover:bg-chat-muted/10",
  },
  fill: {
    primary: "bg-chat-accent text-white hover:bg-chat-accent/80",
    secondary: "bg-chat-muted text-chat-background hover:bg-chat-muted/80",
  },
} as const;

const sizes = {
  sm: "h-[52px] px-8 text-[16px]",
  xs: "h-[40px] px-4 text-[14px]",
  icon: "h-[34px] w-[34px]",
} as const;

type ButtonProps = Omit<
  React.DetailedHTMLProps<React.ButtonHTMLAttributes<HTMLButtonElement>, HTMLButtonElement>,
  "onClick"
> & Partial<{
  className: string;
  leftIcon: React.ReactNode;
  rightIcon: React.ReactNode;
  onClick: () => void;
  shape: keyof typeof shapes;
  variant: keyof typeof variants | null;
  size: keyof typeof sizes;
  color: string;
}>;

const Button: React.FC<React.PropsWithChildren<ButtonProps>> = ({
  children,
  className = "",
  leftIcon,
  rightIcon,
  shape = "round",
  variant = "fill",
  size = "xs",
  color = "primary",
  ...restProps
}) => {
  return (
    <button
      className={`${className} flex flex-row items-center justify-center text-center cursor-pointer whitespace-nowrap font-medium transition-colors ${
        shape && shapes[shape]
      } ${size && sizes[size]} ${
        variant && variants[variant]?.[color as keyof (typeof variants)[typeof variant]]
      }`}
      {...restProps}
    >
      {!!leftIcon && leftIcon}
      {children}
      {!!rightIcon && rightIcon}
    </button>
  );
};

export { Button };
