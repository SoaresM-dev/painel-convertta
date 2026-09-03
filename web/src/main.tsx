import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./estilos.css";

const raiz = document.getElementById("raiz");
/* O `!` (non-null assertion) resolveria isto numa linha, e é exatamente o que
 * o modo estrito existe para desencorajar: ele desliga a verificação em vez de
 * tratar o caso. Se o elemento sumir do index.html, a mensagem abaixo diz o
 * que aconteceu — o `!` daria "Cannot read properties of null". */
if (raiz === null) {
  throw new Error('Elemento #raiz não encontrado no index.html');
}

createRoot(raiz).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
