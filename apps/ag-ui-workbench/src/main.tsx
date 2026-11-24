import React from "react";
import { createRoot } from "react-dom/client";
import "dockview-react/dist/styles/dockview.css";
import "./styles.css";

import App from "./App";
import { initializeOperatorSession } from "./operatorSession";

const root = createRoot(document.getElementById("root")!);
void initializeOperatorSession()
  .then(() => {
    root.render(
      <React.StrictMode>
        <App />
      </React.StrictMode>,
    );
  })
  .catch(() => {
    root.render(<p>Open a current operator launch URL to use the workbench.</p>);
  });
