import type { Color } from "../../domain/chess/types";

type ClockPanelProps = {
  clocks: Record<Color, number>;
  turn: Color;
  phase: "setup" | "playing" | "finished";
  resultReason?: string;
};

export function formatClock(seconds: number): string {
  const safeSeconds = Math.max(0, seconds);
  if (safeSeconds < 10) return `0:00.${Math.floor(safeSeconds * 10)}`;
  const whole = Math.ceil(safeSeconds);
  return `${String(Math.floor(whole / 60)).padStart(2, "0")}:${String(whole % 60).padStart(2, "0")}`;
}

export function ClockPanel({ clocks, turn, phase, resultReason }: ClockPanelProps) {
  const activeLabel = phase === "playing" ? `${turn === "white" ? "White" : "Black"} to move` : phase === "finished" && resultReason ? resultReason : "Game not started";
  return (
    <section className="clock-panel" aria-label="Game clocks">
      <div className={`clock clock-${turn === "white" ? "white" : "black"} ${phase === "playing" && turn === "white" ? "active" : ""} ${clocks.white <= 10 && phase === "playing" ? "low-time" : ""}`}>
        <span className="clock-label">White</span>
        <strong className="clock-time" aria-label={`White clock ${formatClock(clocks.white)}`}>{formatClock(clocks.white)}</strong>
      </div>
      <div className={`clock clock-${turn === "black" ? "black" : "white"} ${phase === "playing" && turn === "black" ? "active" : ""} ${clocks.black <= 10 && phase === "playing" ? "low-time" : ""}`}>
        <span className="clock-label">Black</span>
        <strong className="clock-time" aria-label={`Black clock ${formatClock(clocks.black)}`}>{formatClock(clocks.black)}</strong>
      </div>
      <p className="clock-status" aria-live="polite">{activeLabel}</p>
    </section>
  );
}
