import { useEffect } from "react";
import type { GamePhase } from "./useChessGame";

type ReplayKeyboardOptions = {
  phase: GamePhase;
  stepReplay: (direction: "backward" | "forward") => void;
};

export function useReplayKeyboard({ phase, stepReplay }: ReplayKeyboardOptions): void {
  useEffect(() => {
    if (phase === "setup") return undefined;
    const handleKeyDown = (event: KeyboardEvent) => {
      const target = event.target;
      if (target instanceof HTMLElement && (target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName))) return;
      if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
      event.preventDefault();
      stepReplay(event.key === "ArrowLeft" ? "backward" : "forward");
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [phase, stepReplay]);
}
