import React from 'react';

const shapes = {
  round: "rounded-lg",
} as const;

const variants = {
  outline: {
    blue_gray_800: "border-blue_gray-800 border border-solid text-blue_gray-800",
    primary: "border-[#00a9dd] border border-solid text-[#00a9dd]",
  },
  fill: {
    blue_gray_800: "bg-blue_gray-800 text-white",
    primary: "bg-[#00a9dd] text-white",
  },
} as const;

const sizes = {
  sm: "h-[52px] px-8 text-[16px]",
  xs: "h-[40px] px-2.5 text-[16px]",
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
  shape,
  variant = "fill",
  size = "xs",
  color = "primary",
  ...restProps
}) => {
  return (
    <button
      className={`${className} flex flex-row items-center justify-center text-center cursor-pointer whitespace-nowrap text-[16px] font-medium rounded-lg lg:text-[13px] ${
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