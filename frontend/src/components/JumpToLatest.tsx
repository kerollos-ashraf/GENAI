import { Icon } from "./Icon";

/** Shown when the reader has scrolled up and newer messages are below. */
export function JumpToLatest({ onClick }: { onClick: () => void }) {
  return (
    <button className="jump" onClick={onClick}>
      <Icon name="arrowDown" size={15} /> Latest
    </button>
  );
}
