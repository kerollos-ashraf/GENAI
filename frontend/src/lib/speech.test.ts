import { SpeechController } from "./speech";

class FakeUtterance {
  voice: SpeechSynthesisVoice | null = null;
  lang = "";
  rate = 1;
  onend: (() => void) | null = null;
  constructor(readonly text: string) {}
}

function fakeEngine(voices: Partial<SpeechSynthesisVoice>[] = []) {
  const spoken: FakeUtterance[] = [];
  const synth = {
    speak: vi.fn((u: FakeUtterance) => spoken.push(u)),
    cancel: vi.fn(),
    pause: vi.fn(),
    resume: vi.fn(),
    getVoices: () => voices as SpeechSynthesisVoice[],
    addEventListener: vi.fn(),
  };
  const make = (text: string) => new FakeUtterance(text) as unknown as SpeechSynthesisUtterance;
  const controller = new SpeechController([synth as unknown as SpeechSynthesis, make]);
  return { controller, synth, spoken };
}

beforeEach(() => {
  localStorage.clear();
});

it("speaks clean text sentence by sentence and returns to idle at the end", () => {
  const { controller, spoken } = fakeEngine();
  controller.speak("a1", "Covered up to **$25,000** [p.md § Section 1]. Floods are excluded.", 1.2);

  expect(spoken.map((u) => u.text)).toEqual(["Covered up to $25,000.", "Floods are excluded."]);
  expect(spoken.every((u) => u.rate === 1.2 && u.lang === "en-US")).toBe(true);
  expect(controller.stateOf("a1")).toBe("speaking");

  spoken.at(-1)?.onend?.();
  expect(controller.stateOf("a1")).toBe("idle");
});

it("toggles pause and resume, and only one answer speaks at a time", () => {
  const { controller, synth } = fakeEngine();
  controller.toggle("a1", "First answer.");
  controller.toggle("a1", "First answer.");
  expect(controller.stateOf("a1")).toBe("paused");
  expect(synth.pause).toHaveBeenCalled();

  controller.toggle("a2", "Second answer.");
  expect(controller.stateOf("a2")).toBe("speaking");
  expect(controller.stateOf("a1")).toBe("idle");
});

it("stop(id) ignores answers that aren't speaking", () => {
  const { controller, synth } = fakeEngine();
  controller.speak("a1", "Hello.");
  controller.stop("other");
  expect(synth.cancel).toHaveBeenCalledTimes(1); // only the cancel before speaking
  controller.stop("a1");
  expect(controller.stateOf("a1")).toBe("idle");
});

it("prefers natural voices in the answer's language and remembers the choice", () => {
  const { controller } = fakeEngine([
    { name: "Basic English", lang: "en-US", localService: true },
    { name: "Microsoft Aria Online (Natural)", lang: "en-US", localService: false },
    { name: "Arabic Voice", lang: "ar-EG", localService: true },
  ]);
  expect(controller.preferredVoice("Hello")).toBe("Microsoft Aria Online (Natural)");
  expect(controller.voicesFor("مرحبا").map((v) => v.name)).toEqual(["Arabic Voice"]);

  controller.rememberVoice("Hello", "Basic English");
  expect(controller.preferredVoice("Hello")).toBe("Basic English");
});

it("notifies subscribers and can unsubscribe", () => {
  const { controller } = fakeEngine();
  const listener = vi.fn();
  const unsubscribe = controller.subscribe(listener);
  controller.speak("a1", "Hi.");
  expect(listener).toHaveBeenCalled();
  unsubscribe();
  listener.mockClear();
  controller.stop();
  expect(listener).not.toHaveBeenCalled();
});

it("does nothing without a speech engine", () => {
  const controller = new SpeechController(null);
  expect(controller.supported).toBe(false);
  controller.speak("a1", "Hello.");
  expect(controller.stateOf("a1")).toBe("idle");
});
