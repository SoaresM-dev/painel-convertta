/* O que a linha da tabela esconde.
 *
 * A tabela do resumo responde "quanto custa o lead deste cliente?". A pergunta
 * seguinte é sempre "por causa de qual campanha?", e até aqui não havia onde
 * clicar para descobrir. É o passo que separa uma tabela impressa de uma
 * ferramenta.
 */
import { useCallback, useEffect, useState } from "react";
import {
  api,
  emDataHora,
  emPorcento,
  emReais,
  NaoAutorizado,
  plural,
  type Periodo,
} from "./api";
import { Erro } from "./estados";
import type { DetalheCliente as Detalhe, StatusLead } from "./tipos";
import { ROTULO_CANAL, ROTULO_STATUS } from "./tipos";

const STATUS: StatusLead[] = ["novo", "contatado", "qualificado", "ganho", "perdido"];

interface Props {
  clienteId: number;
  periodo: Periodo;
  aoFechar: () => void;
  aoMudarDados: () => void;
  aoExpirar: () => void;
}

export default function DetalheCliente({
  clienteId,
  periodo,
  aoFechar,
  aoMudarDados,
  aoExpirar,
}: Props) {
  const [detalhe, setDetalhe] = useState<Detalhe | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [mudando, setMudando] = useState<number | null>(null);

  const carregar = useCallback(() => {
    setErro(null);
    api
      .detalhe(clienteId, periodo)
      .then(setDetalhe)
      .catch((e: unknown) => {
        if (e instanceof NaoAutorizado) aoExpirar();
        else setErro(e instanceof Error ? e.message : "Falha ao carregar o cliente");
      });
  }, [clienteId, periodo, aoExpirar]);

  useEffect(carregar, [carregar]);

  useEffect(() => {
    const aoTeclar = (e: KeyboardEvent): void => {
      if (e.key === "Escape") aoFechar();
    };
    window.addEventListener("keydown", aoTeclar);
    return () => window.removeEventListener("keydown", aoTeclar);
  }, [aoFechar]);

  /* Muda o status e recarrega **os dois**: a gaveta e o painel atrás dela. Um
   * lead que vira "ganho" muda a taxa de conversão do cliente, o funil e a
   * série — deixar o número velho na tela de trás seria mostrar duas verdades
   * ao mesmo tempo. */
  async function mudarStatus(leadId: number, status: StatusLead): Promise<void> {
    setMudando(leadId);
    try {
      await api.mudarStatus(leadId, status);
      carregar();
      aoMudarDados();
    } catch (e) {
      if (e instanceof NaoAutorizado) aoExpirar();
      else setErro(e instanceof Error ? e.message : "Não foi possível mudar o status");
    } finally {
      setMudando(null);
    }
  }

  return (
    <div className="cortina" onClick={aoFechar}>
      <aside
        className="gaveta"
        role="dialog"
        aria-modal="true"
        aria-label="Detalhe do cliente"
        onClick={(e) => e.stopPropagation()}
      >
        <header>
          <h2>{detalhe?.cliente ?? "Carregando…"}</h2>
          <button className="fechar" onClick={aoFechar} aria-label="Fechar">
            ×
          </button>
        </header>

        {erro !== null && <Erro mensagem={erro} aoTentarDeNovo={carregar} />}

        {detalhe !== null && (
          <>
            <h3>Campanhas</h3>
            {detalhe.campanhas.length === 0 ? (
              <p className="sutil">Nenhuma campanha ativa neste período.</p>
            ) : (
              <ul className="lista-campanhas">
                {detalhe.campanhas.map((c) => (
                  <li key={c.id}>
                    <div className="campanha-topo">
                      <strong>{c.nome}</strong>
                      <span className={`etiqueta ${c.canal}`}>{ROTULO_CANAL[c.canal]}</span>
                    </div>
                    <div className="campanha-numeros sutil">
                      <span>{emReais(c.investimento_centavos)}</span>
                      <span>{plural(c.leads, "lead", "leads")}</span>
                      <span>{emReais(c.custo_por_lead_centavos)} por lead</span>
                      <span>{emPorcento(c.taxa_conversao)}</span>
                    </div>
                  </li>
                ))}
              </ul>
            )}

            <h3>
              Leads recentes
              {detalhe.leads_recentes.length > 0 && (
                <span className="sutil"> · os {detalhe.leads_recentes.length} últimos</span>
              )}
            </h3>
            {detalhe.leads_recentes.length === 0 ? (
              <p className="sutil">Nenhum lead neste período.</p>
            ) : (
              <table className="leads">
                <thead>
                  <tr>
                    <th>Lead</th>
                    <th>Campanha</th>
                    <th>Quando</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {detalhe.leads_recentes.map((l) => (
                    <tr key={l.id}>
                      <td>
                        {l.nome}
                        {l.email !== null && <span className="sutil bloco">{l.email}</span>}
                      </td>
                      <td className="sutil">{l.campanha}</td>
                      <td className="sutil">{emDataHora(l.criado_em)}</td>
                      <td>
                        {/* O status é o único campo que muda depois do
                            cadastro, e muda o tempo todo. Um `select` na
                            própria linha custa um clique; abrir um formulário
                            para trocar uma palavra custa quatro. */}
                        <select
                          className={`status ${l.status}`}
                          value={l.status}
                          disabled={mudando === l.id}
                          onChange={(e) => void mudarStatus(l.id, e.target.value as StatusLead)}
                          aria-label={`Status de ${l.nome}`}
                        >
                          {STATUS.map((s) => (
                            <option key={s} value={s}>
                              {ROTULO_STATUS[s]}
                            </option>
                          ))}
                        </select>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </>
        )}
      </aside>
    </div>
  );
}
