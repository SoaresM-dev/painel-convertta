import { useEffect, useState } from "react";
import { api, emPorcento, emReais, NaoAutorizado, token } from "./api";
import type { Resumo } from "./tipos";

interface PropsNumero {
  rotulo: string;
  valor: string | number;
  detalhe?: string;
}

function Numero({ rotulo, valor, detalhe }: PropsNumero) {
  return (
    <div className="numero">
      <span className="rotulo">{rotulo}</span>
      <strong>{valor}</strong>
      {detalhe !== undefined && <span className="sutil">{detalhe}</span>}
    </div>
  );
}

interface Props {
  aoSair: () => void;
}

export default function Painel({ aoSair }: Props) {
  const [resumo, setResumo] = useState<Resumo | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    api
      .resumo()
      .then(setResumo)
      .catch((e: unknown) => {
        /* `unknown` e não `any`: o TypeScript obriga a estreitar antes de usar,
         * e é aqui que a distinção entre sessão expirada e erro comum vive. */
        if (e instanceof NaoAutorizado) aoSair();
        else setErro(e instanceof Error ? e.message : "Falha ao carregar");
      });
  }, [aoSair]);

  if (erro !== null) return <p className="erro">{erro}</p>;
  if (resumo === null) return <p className="sutil">Carregando…</p>;

  return (
    <div className="painel">
      <header>
        <h1>Painel Convertta</h1>
        <button
          className="secundario"
          onClick={() => {
            token.limpar();
            aoSair();
          }}
        >
          Sair
        </button>
      </header>

      <section className="numeros">
        <Numero rotulo="Investimento" valor={emReais(resumo.investimento_centavos)} />
        <Numero rotulo="Leads" valor={resumo.leads} detalhe={`${resumo.leads_ganhos} ganhos`} />
        <Numero
          rotulo="Custo por lead"
          valor={emReais(resumo.custo_por_lead_centavos)}
          detalhe={resumo.custo_por_lead_centavos === null ? "sem leads ainda" : "média geral"}
        />
      </section>

      <table>
        <thead>
          <tr>
            <th>Cliente</th>
            <th className="num">Campanhas</th>
            <th className="num">Investimento</th>
            <th className="num">Leads</th>
            <th className="num">Custo/lead</th>
            <th className="num">Conversão</th>
          </tr>
        </thead>
        <tbody>
          {resumo.linhas.map((l) => (
            <tr key={l.cliente_id}>
              <td>{l.cliente}</td>
              <td className="num">{l.campanhas}</td>
              <td className="num">{emReais(l.investimento_centavos)}</td>
              <td className="num">
                {l.leads}
                {l.leads_ganhos > 0 && <span className="sutil"> · {l.leads_ganhos} ganhos</span>}
              </td>
              <td className="num">{emReais(l.custo_por_lead_centavos)}</td>
              <td className="num">{emPorcento(l.taxa_conversao)}</td>
            </tr>
          ))}
          {resumo.linhas.length === 0 && (
            <tr>
              <td colSpan={6} className="sutil">
                Nenhum cliente cadastrado ainda.
              </td>
            </tr>
          )}
        </tbody>
      </table>

      <p className="sutil rodape">
        Um traço no custo por lead significa campanha sem lead ainda — não custo zero.
      </p>
    </div>
  );
}
