import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// Swap the app-wide speech controller for one driven by a fake engine.
const engine = vi.hoisted(() => ({
  synth: {
    speak: vi.fn(),
    cancel: vi.fn(),
    pause: vi.fn(),
    resume: vi.fn(),
    getVoices: () => [
      { name: "Microsoft Aria Online (Natural) - English", lang: "en-US", localService: false },
      { name: "Basic", lang: "en-US", localService: true },
    ],
    addEventListener: vi.fn(),
  },
}));

vi.mock("../lib/speech", async (importOriginal) => {
  const real = await importOriginal<typeof import("../lib/speech")>();
  const make = (text: string) => ({ text }) as unknown as SpeechSynthesisUtterance;
  return {
    ...real,
    speech: new real.SpeechController([engine.synth as unknown as SpeechSynthesis, make]),
  };
});

const { speech } = await import("../lib/speech");
const { VoicePlayer } = await import("./VoicePlayer");

beforeEach(() => {
  speech.stop();
  localStorage.clear();
});

it("plays, pauses and stops one answer", async () => {
  render(<VoicePlayer id="a1" text="Covered up to $25,000." rate={1.1} />);
  expect(screen.getByText("Listen")).toBeInTheDocument();

  await userEvent.click(screen.getByRole("button", { name: "Play answer" }));
  expect(screen.getByText("Speaking…")).toBeInTheDocument();
  expect(engine.synth.speak).toHaveBeenCalled();

  await userEvent.click(screen.getByRole("button", { name: "Pause" }));
  expect(screen.getByText("Paused")).toBeInTheDocument();

  await userEvent.click(screen.getByRole("button", { name: "Stop" }));
  expect(screen.getByText("Listen")).toBeInTheDocument();
});

it("lists natural voices first with short names and remembers the pick", async () => {
  render(<VoicePlayer id="a1" text="Hello there." rate={1} />);
  const picker = screen.getByRole("combobox", { name: "Voice" });
  expect(picker).toHaveValue("Microsoft Aria Online (Natural) - English");
  expect(screen.getByRole("option", { name: "Aria Online (Natural)" })).toBeInTheDocument();

  await userEvent.selectOptions(picker, "Basic");
  expect(localStorage.getItem("omnicare_voice_en")).toBe("Basic");
});

it("resets when another answer starts speaking", () => {
  render(
    <>
      <VoicePlayer id="a1" text="First." rate={1} />
      <VoicePlayer id="a2" text="Second." rate={1} />
    </>,
  );
  act(() => {
    speech.speak("a1", "First.");
  });
  expect(screen.getAllByText("Speaking…")).toHaveLength(1);
  act(() => {
    speech.speak("a2", "Second.");
  });
  expect(screen.getAllByText("Speaking…")).toHaveLength(1);
  expect(screen.getAllByText("Listen")).toHaveLength(1);
});
