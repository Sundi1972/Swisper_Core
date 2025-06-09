import React from 'react';
import { Button } from './Button';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  className?: string;
}

const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  children,
  className = '',
}) => {
  if (!isOpen) return null;

  return (
    <>
      <div 
        className="fixed inset-0 bg-black bg-opacity-50 z-40" 
        onClick={onClose}
      />
      
      <div className={`fixed inset-0 z-50 flex items-center justify-center p-4 ${className}`}>
        <div className="bg-[#141923] border border-[#8f99ad] rounded-lg shadow-lg max-w-6xl w-full max-h-[90vh] overflow-hidden">
          <div className="flex items-center justify-between p-4 border-b border-[#8f99ad]">
            <h2 className="text-lg font-semibold text-[#e5e7eb]">{title}</h2>
            <Button
              variant="outline"
              size="icon"
              onClick={onClose}
              className="text-[#8f99ad] hover:text-[#e5e7eb]"
            >
              ✕
            </Button>
          </div>
          
          <div className="overflow-y-auto max-h-[calc(90vh-80px)]">
            {children}
          </div>
        </div>
      </div>
    </>
  );
};

export default Modal;
