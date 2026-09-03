import { useState, type FormEvent } from "react";
import { entrar } from "./api";

interface Props {
  aoEntrar: () => void;
}

export default function Login({ aoEntrar }: Props) {
  const [email, setEmail] = useState("demo@convertta.com.br");
  const [senha, setSenha] = useState("demo1234");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar(evento: FormEvent<HTMLFormElement>): Promise<void> {
    evento.preventDefault();
    setErro(null);
    setEnviando(true);
    try {
      await entrar(email, senha);
      aoEntrar();
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Falha ao entrar");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="tela-login">
      <form className="cartao" onSubmit={enviar}>
        <h1>Painel Convertta</h1>
        <p className="sutil">Leads e campanhas num lugar só.</p>

        <label>
          E-mail
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </label>
        <label>
          Senha
          <input type="password" value={senha} onChange={(e) => setSenha(e.target.value)} required />
        </label>

        {erro !== null && <p className="erro">{erro}</p>}

        <button type="submit" disabled={enviando}>
          {enviando ? "Entrando…" : "Entrar"}
        </button>

        <p className="sutil demo">Conta demo já preenchida — é só entrar.</p>
      </form>
    </div>
  );
}
