import { HashRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/layout/AppShell";
import { HistoryPage } from "./routes/HistoryPage";
import { HomePage } from "./routes/HomePage";
import { PlayPage } from "./routes/PlayPage";
import { TrainingPage } from "./routes/TrainingPage";

export function App() {
  return (
    <HashRouter>
      <AppShell>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/play" element={<PlayPage />} />
          <Route path="/training" element={<TrainingPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AppShell>
    </HashRouter>
  );
}
