import { SUGGESTIONS } from "../config";
import { Icon } from "./Icon";
import "./Intro.css";

interface Props {
  onAsk: (question: string) => void;
  disabled: boolean;
}

/** Empty state: one question and tap-to-ask suggestions. */
export function Intro({ onAsk, disabled }: Props) {
  return (
    <section className="intro" data-testid="intro">
      <h1 className="greet">How can we help with your policy?</h1>
      <p className="lede">
        Ask about your coverage, check a claim, or file a new one. Type below, or tap the mic and
        speak in English or Arabic.
      </p>
      <div className="suggestions">
        {SUGGESTIONS.map(({ label, question, icon }) => (
          <button
            key={label}
            className="suggestion"
            onClick={() => {
              onAsk(question);
            }}
            disabled={disabled}
          >
            <span className="suggestion-icon" aria-hidden="true">
              <Icon name={icon} size={18} />
            </span>
            {label}
          </button>
        ))}
      </div>
    </section>
  );
}
