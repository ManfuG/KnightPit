import { Capacitor } from "@capacitor/core";
import { setupAndroidEntry } from "./entry";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./styles/index.css";
import "./styles/mobile.css";

if (Capacitor.getPlatform() === "android") {
  document.documentElement.classList.add("android");
  setupAndroidEntry();
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
