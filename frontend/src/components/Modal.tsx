import type { ReactNode } from "react";

import { useEscapeKey } from "../lib/useEscapeKey";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  footer?: ReactNode;
}

export function Modal({ open, onClose, title, children, footer }: ModalProps) {
  useEscapeKey(onClose, open);

  if (!open) return null;

  return (
    <div className="modal" onClick={onClose}>
      <div className="mbox" onClick={(e) => e.stopPropagation()}>
        <div className="mhead">
          <h2>{title}</h2>
          <div className="hgap" />
          <button className="btn btn-s btn-sm" onClick={onClose}>
            Close
          </button>
        </div>
        <div className="mbody">{children}</div>
        {footer && <div className="mfoot">{footer}</div>}
      </div>
    </div>
  );
}
