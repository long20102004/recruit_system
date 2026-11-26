import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./styles/main.css";
import "./styles/hl.css";
import App from "./App.tsx";

document.body.classList.add("hl");

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
