import { describe, expect, it } from "vitest";

import { normalizeVoiceState } from "@/lib/api/normalize";
import {
  audioDataUrl,
  clipBase64,
  pickVoiceInputMode,
  pickVoiceOutputMode,
  speechLang,
} from "./voice";

/**
 * The voice seam's choices (19.6), as pure decisions.
 *
 * The hook around them touches MediaRecorder, SpeechRecognition and Audio --
 * none of which jsdom implements -- so the decisions that must be right are
 * kept here, where they can be stated: the deployment's provider wins when it
 * exists, the browser's own speech is the fallback, and typing is always the
 * last resort rather than an error.
 */

describe("voice input mode", () => {
  it("uses the deployment's ears when it has them", () => {
    expect(pickVoiceInputMode(true, true)).toBe("service");
    expect(pickVoiceInputMode(true, false)).toBe("service");
  });

  it("falls back to the browser's recognition when the deployment has none", () => {
    expect(pickVoiceInputMode(false, true)).toBe("browser");
  });

  it("falls back to typing when neither side can listen", () => {
    expect(pickVoiceInputMode(false, false)).toBe("typing");
  });
});

describe("voice output mode", () => {
  it("prefers the provider's voice, then the browser's, then silence", () => {
    expect(pickVoiceOutputMode(true, true)).toBe("service");
    expect(pickVoiceOutputMode(false, true)).toBe("browser");
    expect(pickVoiceOutputMode(false, false)).toBe("none");
  });
});

describe("the recorded clip's container", () => {
  it("base64s the blob's bytes and nothing else", async () => {
    expect(await clipBase64(new Blob([new Uint8Array([0, 1, 2, 250])]))).toBe("AAEC+g==");
    expect(await clipBase64(new Blob([]))).toBe("");
  });

  it("rebuilds a playable url, defaulting the mime rather than emitting audio/undefined", () => {
    expect(audioDataUrl("audio/wav", "AAAA")).toBe("data:audio/wav;base64,AAAA");
    expect(audioDataUrl("", "AAAA")).toBe("data:audio/wav;base64,AAAA");
  });
});

describe("the recognition language", () => {
  it("names a locale the browser's recognizers know", () => {
    expect(speechLang("zh")).toBe("zh-CN");
    expect(speechLang("en")).toBe("en-US");
  });
});

describe("normalizeVoiceState", () => {
  it("reads a configured deployment as it stands", () => {
    expect(normalizeVoiceState({ provider: "mock", stt: true, tts: true })).toEqual({
      provider: "mock",
      stt: true,
      tts: true,
    });
  });

  it("treats an absent or malformed answer as no provider, never as capability", () => {
    expect(normalizeVoiceState(null)).toEqual({ provider: "", stt: false, tts: false });
    expect(normalizeVoiceState("nonsense")).toEqual({ provider: "", stt: false, tts: false });
    // A provider name without capability flags is not invented into a capable one.
    expect(normalizeVoiceState({ provider: "openai_compat" })).toEqual({
      provider: "openai_compat",
      stt: false,
      tts: false,
    });
  });

  it("reads the boolean strings a serializer may emit", () => {
    expect(normalizeVoiceState({ provider: "mock", stt: "true", tts: "false" })).toEqual({
      provider: "mock",
      stt: true,
      tts: false,
    });
  });
});
