import { useEffect, useRef } from "react";
import { REPLY_MODES, THEMES, USER_ID_PATTERN } from "../config";
import type { Preferences } from "../hooks/usePreferences";
import { Icon } from "./Icon";
import { KnowledgeBase } from "./KnowledgeBase";
import "./Sidebar.css";

interface Props {
  prefs: Preferences;
  open: boolean;
  onClose: () => void;
  onNewConversation: () => void;
}

/** Settings. A fixed column on wide screens; a drawer (Escape closes it) on phones. */
export function Sidebar({ prefs, open, onClose, onNewConversation }: Props) {
  const closeButton = useRef<HTMLButtonElement>(null);
  const validId = USER_ID_PATTERN.test(prefs.userId);

  useEffect(() => {
    if (!open) return;
    closeButton.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
    };
  }, [open, onClose]);

  return (
    <>
      <div className={`scrim${open ? " show" : ""}`} onClick={onClose} aria-hidden="true" />
      <aside className={`sidebar${open ? " open" : ""}`} aria-label="Settings">
        <div className="sidebar-head">
          <h2>Your session</h2>
          <button
            ref={closeButton}
            className="icon-button close-button"
            onClick={onClose}
            aria-label="Close settings"
          >
            <Icon name="close" />
          </button>
        </div>

        <label className="field">
          User ID
          <input
            value={prefs.userId}
            onChange={(e) => {
              prefs.setUserId(e.target.value.trim());
            }}
            aria-invalid={!validId}
            spellCheck={false}
          />
          {!validId && <small className="invalid">Letters, numbers, - and _ only.</small>}
        </label>
        <button className="button" onClick={onNewConversation}>
          <Icon name="plus" size={16} /> New conversation
        </button>

        <details className="panel">
          <summary>
            <Icon name="wave" /> Voice replies
          </summary>
          <fieldset className="radios">
            <legend>Read answers aloud</legend>
            {REPLY_MODES.map(({ value, label }) => (
              <label key={value}>
                <input
                  type="radio"
                  name="reply-mode"
                  checked={prefs.replyMode === value}
                  onChange={() => {
                    prefs.setReplyMode(value);
                  }}
                />
                {label}
              </label>
            ))}
          </fieldset>
          <label className="field">
            <span>
              Speaking speed <output>{prefs.rate.toFixed(2)}×</output>
            </span>
            <input
              type="range"
              min={0.7}
              max={1.5}
              step={0.05}
              value={prefs.rate}
              onChange={(e) => {
                prefs.setRate(Number(e.target.value));
              }}
            />
          </label>
          <p className="muted">Pick a voice from the player under any answer.</p>
        </details>

        <KnowledgeBase />

        <fieldset className="segmented" aria-label="Appearance">
          <legend className="visually-hidden">Appearance</legend>
          {THEMES.map(({ value, label, icon }) => (
            <label key={value} title={`${label} theme`}>
              <input
                type="radio"
                name="theme"
                checked={prefs.theme === value}
                onChange={() => {
                  prefs.setTheme(value);
                }}
              />
              {icon && <Icon name={icon} size={15} />}
              <span>{label}</span>
            </label>
          ))}
        </fieldset>
      </aside>
    </>
  );
}
