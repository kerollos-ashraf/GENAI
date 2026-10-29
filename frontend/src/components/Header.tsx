import type { Ref } from "react";
import "./Header.css";
import { Icon } from "./Icon";

export function BrandMark() {
  return (
    <span className="mark">
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M12 2.5 4 5.6v6.1c0 4.8 3.4 8.6 8 9.8 4.6-1.2 8-5 8-9.8V5.6L12 2.5Z" />
        <path className="tick" d="m8.4 12.2 2.5 2.5 4.8-5" />
      </svg>
    </span>
  );
}

const STATUS = {
  checking: "Connecting…",
  online: "Online",
  offline: "Can't reach the service",
} as const;

interface Props {
  online: boolean | null;
  onMenu: () => void;
  menuButtonRef?: Ref<HTMLButtonElement>;
}

export function Header({ online, onMenu, menuButtonRef }: Props) {
  const status = online === null ? "checking" : online ? "online" : "offline";
  return (
    <header className="brand">
      <button
        ref={menuButtonRef}
        className="icon-button menu-button"
        onClick={onMenu}
        aria-label="Open settings"
      >
        <Icon name="menu" />
      </button>
      <BrandMark />
      <div className="name">
        OmniCare
        <small>Policy and claims help</small>
      </div>
      <span className={`status ${status}`} data-testid="status" role="status">
        {STATUS[status]}
      </span>
    </header>
  );
}
