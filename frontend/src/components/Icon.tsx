/** A small stroke icon set (24px grid), so the UI needs no icon library. */
const PATHS = {
  mic: "M12 15a3 3 0 0 0 3-3V6a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3Zm6-3a6 6 0 0 1-12 0m6 6v3",
  send: "M5 12h13M13 6l6 6-6 6",
  close: "M6 6l12 12M18 6 6 18",
  check: "M5 12.5l4.5 4.5L19 7.5",
  play: "M8 5.5v13l11-6.5-11-6.5Z",
  pause: "M8 5v14M16 5v14",
  stop: "M7 7h10v10H7z",
  menu: "M4 7h16M4 12h16M4 17h16",
  plus: "M12 5v14M5 12h14",
  trash: "M5 7h14M10 7V5h4v2m-7 0 1 12h8l1-12",
  refresh: "M19 8a8 8 0 1 0 1 6m-1-6V4m0 4h-4",
  upload: "M12 16V5m-5 5 5-5 5 5M5 19h14",
  tool: "M14.5 6.5a4 4 0 0 0 5 5L13 18a2.1 2.1 0 0 1-3-3l6.5-6.5Zm-9 13 3-3",
  person: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm-7 8a7 7 0 0 1 14 0",
  shield: "M12 3 5 5.8v5.5c0 4.3 3 7.8 7 9 4-1.2 7-4.7 7-9V5.8L12 3Z",
  doc: "M7 3h7l4 4v14H7V3Zm7 0v4h4",
  wave: "M4 10v4M8 7v10M12 4v16M16 7v10M20 10v4",
  books: "M5 4h4v16H5zM10 4h4v16h-4zM15.5 4.5l3.8-1 3.7 15.5-3.8 1z",
  copy: "M9 9h10v11H9zM5 15V4h10",
  drop: "M12 3.5s6 6.4 6 10.5a6 6 0 0 1-12 0c0-4.1 6-10.5 6-10.5Z",
  umbrella: "M3 12a9 9 0 0 1 18 0H3Zm9 0v6.5a2 2 0 0 1-4 0M12 3v0",
  search: "M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14Zm9 2-4-4",
  arrowDown: "M12 5v14m-6-6 6 6 6-6",
  sun: "M12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm0-14v2m0 16v2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M2 12h2m16 0h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4",
  moon: "M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5Z",
  monitor: "M3 5h18v11H3zM8 20h8m-4-4v4",
  alert:
    "M12 8v5m0 3.5v.5M10.3 3.9 2.6 17a2 2 0 0 0 1.7 3h15.4a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z",
} as const;

export type IconName = keyof typeof PATHS;

export function Icon({ name, size = 18 }: { name: IconName; size?: number }) {
  const filled = name === "play" || name === "stop";
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      aria-hidden="true"
      fill={filled ? "currentColor" : "none"}
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d={PATHS[name]} />
    </svg>
  );
}
