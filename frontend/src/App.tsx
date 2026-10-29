import { useCallback, useRef, useState } from "react";
import "./App.css";
import { Composer } from "./components/Composer";
import { Header } from "./components/Header";
import { Intro } from "./components/Intro";
import { JumpToLatest } from "./components/JumpToLatest";
import { MessageBubble, Thinking } from "./components/MessageBubble";
import { Sidebar } from "./components/Sidebar";
import { DEFAULT_USER_ID, USER_ID_PATTERN } from "./config";
import { useAutoScroll } from "./hooks/useAutoScroll";
import { useChat } from "./hooks/useChat";
import { useHealth } from "./hooks/useHealth";
import { usePreferences } from "./hooks/usePreferences";

const ACTIVITY_LABEL = { transcribing: "Transcribing…", thinking: "Checking…" } as const;

export default function App() {
  const prefs = usePreferences();
  const online = useHealth();
  const chat = useChat({
    userId: USER_ID_PATTERN.test(prefs.userId) ? prefs.userId : DEFAULT_USER_ID,
    replyMode: prefs.replyMode,
    rate: prefs.rate,
  });
  const [menuOpen, setMenuOpen] = useState(false);
  const menuButton = useRef<HTMLButtonElement>(null);
  const scroller = useRef<HTMLElement>(null);
  const { showJump, scrollToBottom } = useAutoScroll(
    scroller,
    `${chat.messages.length}:${chat.activity}`,
  );
  const busy = chat.activity !== "idle";
  const empty = chat.messages.length === 0 && !busy;

  const closeMenu = useCallback(() => {
    if (menuOpen) menuButton.current?.focus(); // back to where the drawer was opened from
    setMenuOpen(false);
  }, [menuOpen]);

  const newConversation = () => {
    chat.reset();
    closeMenu();
  };

  return (
    <div className="layout">
      <Sidebar
        prefs={prefs}
        open={menuOpen}
        onClose={closeMenu}
        onNewConversation={newConversation}
      />
      <main className="main" ref={scroller}>
        <div className="column">
          <Header
            online={online}
            menuButtonRef={menuButton}
            onMenu={() => {
              setMenuOpen(true);
            }}
          />
          {empty ? (
            <Intro onAsk={(q) => void chat.ask(q)} disabled={busy} />
          ) : (
            <section className="conversation" aria-label="Conversation" aria-live="polite">
              {chat.messages.map((m) => (
                <MessageBubble
                  key={m.id}
                  message={m}
                  rate={prefs.rate}
                  onRetry={(failed) => void chat.retry(failed)}
                />
              ))}
              {chat.activity !== "idle" && (
                <Thinking label={ACTIVITY_LABEL[chat.activity]} onStop={chat.cancel} />
              )}
            </section>
          )}
        </div>
        <div className="dock">
          {showJump && !empty && (
            <JumpToLatest
              onClick={() => {
                scrollToBottom();
              }}
            />
          )}
          <Composer
            busy={busy}
            notice={chat.notice}
            onSend={(t) => void chat.ask(t)}
            onVoice={(audio, name) => void chat.askByVoice(audio, name)}
          />
        </div>
      </main>
    </div>
  );
}
