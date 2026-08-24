import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Icon } from "../components/ui/Icon";
import { LinkButton, Panel } from "../components/ui/Primitives";
import {
  HISTORY_DISPLAY_LIMIT,
  HISTORY_STORAGE_KEY,
  HISTORY_UPDATED_EVENT,
  readGameHistory,
  type HistoryEntry,
} from "../domain/chess/history";

const reasonLabels: Record<HistoryEntry["result"]["reason"], string> = {
  checkmate: "Checkmate",
  timeout: "Time",
  resignation: "Resignation",
  "draw-agreement": "Draw by agreement",
  stalemate: "Stalemate",
  "insufficient-material": "Insufficient material",
};

function resultLabel(entry: HistoryEntry): string {
  const winner = entry.result.winner
    ? entry.playerColor ? (entry.result.winner === entry.playerColor ? "User wins" : "AI wins") : `${entry.result.winner === "white" ? "White" : "Black"} wins`
    : "Draw";
  return `${winner} · ${reasonLabels[entry.result.reason]}`;
}

function formatDate(createdAt: string): string {
  const date = new Date(createdAt);
  return Number.isNaN(date.getTime()) ? "—" : new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(date);
}

function formatTime(createdAt: string): string {
  const date = new Date(createdAt);
  return Number.isNaN(date.getTime()) ? "—" : new Intl.DateTimeFormat(undefined, { timeStyle: "short" }).format(date);
}

export function HistoryPage() {
  const navigate = useNavigate();
  const [history, setHistory] = useState<HistoryEntry[]>(() => readGameHistory());

  useEffect(() => {
    const refresh = () => setHistory(readGameHistory());
    const handleStorage = (event: StorageEvent) => {
      if (event.key === HISTORY_STORAGE_KEY || event.key === null) refresh();
    };
    window.addEventListener("storage", handleStorage);
    window.addEventListener(HISTORY_UPDATED_EVENT, refresh);
    return () => {
      window.removeEventListener("storage", handleStorage);
      window.removeEventListener(HISTORY_UPDATED_EVENT, refresh);
    };
  }, []);

  const openEntry = (entry: HistoryEntry) => {
    navigate(`/training?history=${encodeURIComponent(entry.id)}`);
  };

  const visibleHistory = history.slice(0, HISTORY_DISPLAY_LIMIT);

  return (
    <>
      <header className="page-header">
        <div>
          <p className="eyebrow">Your archive</p>
          <h1>History</h1>
        </div>
      </header>

      <section aria-label="History">
        <Panel className="table-shell">
          <div className="history-table-wrap">
            <table className="history-table">
              <thead><tr><th>Date</th><th>Time</th><th>Result</th><th>Mode</th></tr></thead>
              <tbody>
                {history.length === 0 ? (
                  <tr><td colSpan={4}>
                    <div className="empty-state">
                      <div>
                        <div className="empty-icon"><Icon name="history" width={25} height={25} /></div>
                        <h2>No games yet.</h2>
                        <p>Your first completed game can stay here when history is connected.</p>
                        <LinkButton to="/play" variant="primary" icon="arrow-up-right">Go to play</LinkButton>
                      </div>
                    </div>
                  </td></tr>
                ) : visibleHistory.map((entry) => (
                  <tr
                    key={entry.id}
                    className="history-row"
                    role="link"
                    tabIndex={0}
                    aria-label={`Open ${resultLabel(entry)} from ${formatDate(entry.createdAt)}`}
                    onClick={() => openEntry(entry)}
                    onKeyDown={(event) => {
                      if (event.key !== "Enter" && event.key !== " ") return;
                      event.preventDefault();
                      openEntry(entry);
                    }}
                  >
                    <td>{formatDate(entry.createdAt)}</td>
                    <td>{formatTime(entry.createdAt)}</td>
                    <td>{resultLabel(entry)}</td>
                    <td>{entry.mode === "play" ? `Play · ${entry.timeControl}` : "Training · Untimed"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      </section>
    </>
  );
}
