/* Cadastro de cliente, campanha e lead.
 *
 * **As quatro rotas já existiam e estavam inalcançáveis.** `POST /api/clientes`,
 * `POST /api/campanhas`, `POST /api/leads` e `PATCH /api/leads/{id}` foram
 * escritas e testadas no primeiro dia do projeto; o `api.ts` só chamava o
 * resumo. A demo era somente-leitura por acidente de front-end, não por
 * decisão de escopo — e um painel em que não se pode fazer nada não demonstra
 * um CRUD, demonstra um relatório.
 */
import { useEffect, useState, type FormEvent } from "react";
import { api, emISO, NaoAutorizado } from "./api";
import type { Campanha, Canal, Cliente, StatusLead } from "./tipos";
import { ROTULO_CANAL, ROTULO_STATUS } from "./tipos";

export type Aba = "cliente" | "campanha" | "lead";

const ABAS: { chave: Aba; rotulo: string }[] = [
  { chave: "cliente", rotulo: "Cliente" },
  { chave: "campanha", rotulo: "Campanha" },
  { chave: "lead", rotulo: "Lead" },
];

const STATUS: StatusLead[] = ["novo", "contatado", "qualificado", "ganho", "perdido"];
const CANAIS: Canal[] = ["google_ads", "meta_ads"];

interface Props {
  abaInicial: Aba;
  aoFechar: () => void;
  aoSalvar: () => void;
  aoExpirar: () => void;
}

export default function NovoRegistro({ abaInicial, aoFechar, aoSalvar, aoExpirar }: Props) {
  const [aba, setAba] = useState<Aba>(abaInicial);
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [campanhas, setCampanhas] = useState<Campanha[]>([]);
  const [erro, setErro] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);

  // cliente
  const [nomeCliente, setNomeCliente] = useState("");
  // campanha
  const [clienteId, setClienteId] = useState("");
  const [nomeCampanha, setNomeCampanha] = useState("");
  const [canal, setCanal] = useState<Canal>("google_ads");
  const [investimento, setInvestimento] = useState("");
  /* `toISOString()` passa por UTC e devolve ontem em fuso negativo — o campo
   abriria com a data errada para quem está no Brasil. */
  const [inicio, setInicio] = useState(emISO(new Date()));
  const [fim, setFim] = useState("");
  // lead
  const [campanhaId, setCampanhaId] = useState("");
  const [nomeLead, setNomeLead] = useState("");
  const [email, setEmail] = useState("");
  const [telefone, setTelefone] = useState("");
  const [status, setStatus] = useState<StatusLead>("novo");

  useEffect(() => {
    Promise.all([api.clientes(), api.campanhas()])
      .then(([c, k]) => {
        setClientes(c);
        setCampanhas(k);
      })
      .catch((e: unknown) => {
        if (e instanceof NaoAutorizado) aoExpirar();
        else setErro(e instanceof Error ? e.message : "Falha ao carregar as listas");
      });
  }, [aoExpirar]);

  /* Esc fecha. É o atalho que todo mundo tenta antes de procurar o X, e
   * deixá-lo de fora transforma um diálogo numa armadilha para quem navega
   * pelo teclado. */
  useEffect(() => {
    const aoTeclar = (e: KeyboardEvent): void => {
      if (e.key === "Escape") aoFechar();
    };
    window.addEventListener("keydown", aoTeclar);
    return () => window.removeEventListener("keydown", aoTeclar);
  }, [aoFechar]);

  const nomeDoCliente = (id: number): string =>
    clientes.find((c) => c.id === id)?.nome ?? "Cliente removido";

  async function enviar(evento: FormEvent<HTMLFormElement>): Promise<void> {
    evento.preventDefault();
    setErro(null);
    setSalvando(true);
    try {
      if (aba === "cliente") {
        await api.criarCliente(nomeCliente.trim());
      } else if (aba === "campanha") {
        await api.criarCampanha({
          cliente_id: Number(clienteId),
          nome: nomeCampanha.trim(),
          canal,
          /* Reais entram pela tela, centavos vão para a API. A conversão mora
           * aqui, na borda, exatamente como a de saída em `emReais` — o resto
           * do sistema, dos dois lados, só conhece inteiro. */
          investimento_centavos: Math.round(Number(investimento.replace(",", ".")) * 100),
          inicio,
          ...(fim !== "" ? { fim } : {}),
        });
      } else {
        await api.criarLead({
          campanha_id: Number(campanhaId),
          nome: nomeLead.trim(),
          ...(email !== "" ? { email } : {}),
          ...(telefone !== "" ? { telefone } : {}),
          status,
        });
      }
      aoSalvar();
      aoFechar();
    } catch (e) {
      if (e instanceof NaoAutorizado) aoExpirar();
      else setErro(e instanceof Error ? e.message : "Não foi possível salvar");
    } finally {
      setSalvando(false);
    }
  }

  const semCliente = clientes.length === 0;
  const semCampanha = campanhas.length === 0;

  return (
    <div className="cortina" onClick={aoFechar}>
      <div
        className="dialogo"
        role="dialog"
        aria-modal="true"
        aria-label="Novo registro"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="abas">
          {ABAS.map((a) => (
            <button
              key={a.chave}
              type="button"
              className={`aba ${aba === a.chave ? "ativa" : ""}`}
              onClick={() => {
                setAba(a.chave);
                setErro(null);
              }}
            >
              {a.rotulo}
            </button>
          ))}
          <button type="button" className="fechar" onClick={aoFechar} aria-label="Fechar">
            ×
          </button>
        </div>

        <form onSubmit={enviar}>
          {aba === "cliente" && (
            <label>
              Nome do cliente
              <input
                value={nomeCliente}
                onChange={(e) => setNomeCliente(e.target.value)}
                placeholder="Padaria do Zé"
                minLength={2}
                maxLength={120}
                required
                autoFocus
              />
            </label>
          )}

          {aba === "campanha" &&
            (semCliente ? (
              <p className="sutil">Cadastre um cliente antes — campanha precisa de dono.</p>
            ) : (
              <>
                <label>
                  Cliente
                  <select
                    value={clienteId}
                    onChange={(e) => setClienteId(e.target.value)}
                    required
                  >
                    <option value="">Selecione…</option>
                    {clientes.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.nome}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Nome da campanha
                  <input
                    value={nomeCampanha}
                    onChange={(e) => setNomeCampanha(e.target.value)}
                    placeholder="Encomendas de festa"
                    minLength={2}
                    maxLength={160}
                    required
                  />
                </label>
                <div className="par">
                  <label>
                    Canal
                    <select value={canal} onChange={(e) => setCanal(e.target.value as Canal)}>
                      {CANAIS.map((c) => (
                        <option key={c} value={c}>
                          {ROTULO_CANAL[c]}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Investimento (R$)
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      value={investimento}
                      onChange={(e) => setInvestimento(e.target.value)}
                      placeholder="960,00"
                      required
                    />
                  </label>
                </div>
                <div className="par">
                  <label>
                    Início
                    <input
                      type="date"
                      value={inicio}
                      onChange={(e) => setInicio(e.target.value)}
                      required
                    />
                  </label>
                  <label>
                    Fim <span className="sutil">(vazio = no ar)</span>
                    <input type="date" value={fim} onChange={(e) => setFim(e.target.value)} />
                  </label>
                </div>
              </>
            ))}

          {aba === "lead" &&
            (semCampanha ? (
              <p className="sutil">Cadastre uma campanha antes — lead precisa de origem.</p>
            ) : (
              <>
                <label>
                  Campanha
                  <select
                    value={campanhaId}
                    onChange={(e) => setCampanhaId(e.target.value)}
                    required
                  >
                    <option value="">Selecione…</option>
                    {campanhas.map((c) => (
                      <option key={c.id} value={c.id}>
                        {nomeDoCliente(c.cliente_id)} — {c.nome}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Nome
                  <input
                    value={nomeLead}
                    onChange={(e) => setNomeLead(e.target.value)}
                    minLength={2}
                    maxLength={160}
                    required
                  />
                </label>
                <div className="par">
                  <label>
                    E-mail <span className="sutil">(opcional)</span>
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                    />
                  </label>
                  <label>
                    Telefone <span className="sutil">(opcional)</span>
                    <input
                      value={telefone}
                      onChange={(e) => setTelefone(e.target.value)}
                      maxLength={40}
                    />
                  </label>
                </div>
                <label>
                  Status
                  <select
                    value={status}
                    onChange={(e) => setStatus(e.target.value as StatusLead)}
                  >
                    {STATUS.map((s) => (
                      <option key={s} value={s}>
                        {ROTULO_STATUS[s]}
                      </option>
                    ))}
                  </select>
                </label>
              </>
            ))}

          {erro !== null && <p className="erro">{erro}</p>}

          <div className="acoes">
            <button type="button" className="secundario" onClick={aoFechar}>
              Cancelar
            </button>
            <button
              type="submit"
              disabled={
                salvando ||
                (aba === "campanha" && semCliente) ||
                (aba === "lead" && semCampanha)
              }
            >
              {salvando ? "Salvando…" : "Salvar"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
