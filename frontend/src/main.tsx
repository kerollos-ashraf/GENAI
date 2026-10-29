import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { ClientProvider } from "./api/ClientContext";
import { OmniCareClient } from "./api/client";
import App from "./App";
import { ErrorBoundary } from "./components/ErrorBoundary";
import "./styles/tokens.css";
import "./styles/base.css";

const root = document.getElementById("root");
if (!root) throw new Error("index.html is missing <div id='root'>");

createRoot(root).render(
  <StrictMode>
    <ErrorBoundary>
      <ClientProvider client={new OmniCareClient()}>
        <App />
      </ClientProvider>
    </ErrorBoundary>
  </StrictMode>,
);
