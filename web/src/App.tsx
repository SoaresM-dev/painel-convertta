import { useState } from "react";
import Login from "./Login";
import Painel from "./Painel";
import { token } from "./api";

export default function App() {
  const [autenticado, setAutenticado] = useState(token.ler() !== null);

  return autenticado ? (
    <Painel aoSair={() => setAutenticado(false)} />
  ) : (
    <Login aoEntrar={() => setAutenticado(true)} />
  );
}
