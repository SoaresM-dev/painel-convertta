import { useCallback, useEffect, useMemo, useState } from "react";
import {
  api,
  emNumero,
  emPorcento,
  plural,
  emReais,
  NaoAutorizado,
  token,
  ultimosDias,
  type Periodo,
} from "./api";
import DetalheCliente from "./DetalheCliente";
import { AvisoDeDespertar, Erro, Esqueleto, useDemora, Vazio } from "./estados";
import NovoRegistro, { type Aba } from "./formularios";
import { BarrasDeCanal, FunilDeStatus, SerieDeLeads } from "./graficos";
import type { LinhaResumo, Usuario, Visao } from "./tipos";

/* 90 dias é o padrão porque é o recorte em que a demo tem história para
 * contar: a campanha mais antiga começou nessa janela. Um painel que abre
 * numa semana vazia é tecnicamente correto e comercialmente inútil. */
const PRESETS = [
  { chave: "7", rotulo: "7 dias" },
  { chave: "30", rotulo: "30 dias" },
  { chave: "90", rotulo: "90 dias" },
  { chave: "tudo", rotulo: "Tudo" },
] as const;

type Preset = (typeof PRESETS)[number]["chave"];

function periodoDe(preset: Preset): Periodo {
  if (preset === "tudo") return {};
  return ultimosDias(Number(preset));
}

type Coluna = keyof Pick<
  LinhaResumo,
  "cliente" | "campanhas" | "investimento_centavos" | "leads" | "custo_por_lead_centavos" | "taxa_conversao"
>;

const COLUNAS: { chave: Coluna; rotulo: string; numerica: boolean }[] = [
  { chave: "cliente", rotulo: "Cliente", numerica: false },
  { chave: "campanhas", rotulo: "Campanhas", numerica: true },
  { chave: "investimento_centavos", rotulo: "Investimento", numerica: true },
  { chave: "leads", rotulo: "Leads", numerica: true },
  { chave: "custo_por_lead_centavos", rotulo: "Custo/lead", numerica: true },
  { chave: "taxa_conversao", rotulo: "Conversão", numerica: true },
];

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
  const [preset, setPreset] = useState<Preset>("90");
  /* Sem o `useMemo`, `periodoDe` devolveria um objeto novo a cada render, o
   * `useCallback` abaixo mudaria de identidade junto, e o `useEffect` que
   * depende dele entraria em laço infinito de requisições. */
  const periodo = useMemo(() => periodoDe(preset), [preset]);

  const [visao, setVisao] = useState<Visao | null>(null);
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [atualizadoEm, setAtualizadoEm] = useState<Date | null>(null);

  const [clienteAberto, setClienteAberto] = useState<number | null>(null);
  const [formulario, setFormulario] = useState<Aba | null>(null);
  const [ordem, setOrdem] = useState<{ coluna: Coluna; crescente: boolean }>({
    coluna: "cliente",
    crescente: true,
  });

  const expirou = useCallback(() => {
    token.limpar();
    aoSair();
  }, [aoSair]);

  const carregar = useCallback(() => {
    setCarregando(true);
    setErro(null);
    api
      .visao(periodo)
      .then((v) => {
        setVisao(v);
        setAtualizadoEm(new Date());
      })
      .catch((e: unknown) => {
        if (e instanceof NaoAutorizado) expirou();
        else setErro(e instanceof Error ? e.message : "Falha ao carregar");
      })
      .finally(() => setCarregando(false));
  }, [periodo, expirou]);

  useEffect(carregar, [carregar]);

  /* O nome de quem entrou é carregado uma vez só: ele não muda com o filtro
   * de período, e repetir a chamada a cada troca de recorte seria uma ida à
   * rede para reconfirmar algo que já se sabe. */
  useEffect(() => {
    api
      .eu()
      .then(setUsuario)
      .catch(() => {
        /* Falhar aqui não justifica derrubar o painel: o nome no cabeçalho é
         * cortesia, não informação. Um 401 já é tratado na carga principal. */
      });
  }, []);

  const demorou = useDemora(carregando);
  const primeiraCarga = visao === null;

  const linhas = useMemo(() => {
    if (visao === null) return [];
    const { coluna, crescente } = ordem;
    const sinal = crescente ? 1 : -1;
    return [...visao.resumo.linhas].sort((a, b) => {
      const x = a[coluna];
      const y = b[coluna];
      /* `null` no custo por lead significa "ainda não dá para saber". Ele vai
       * sempre para o fim, nos dois sentidos da ordenação: campanha sem lead
       * não é a mais barata nem a mais cara — ela está fora da comparação. */
      if (x === null) return 1;
      if (y === null) return -1;
      if (typeof x === "string" && typeof y === "string") {
        return sinal * x.localeCompare(y, "pt-BR");
      }
      return sinal * (Number(x) - Number(y));
    });
  }, [visao, ordem]);

  function ordenarPor(coluna: Coluna): void {
    setOrdem((atual) =>
      atual.coluna === coluna
        ? { coluna, crescente: !atual.crescente }
        : { coluna, crescente: coluna === "cliente" }
    );
  }

  return (
    <div className="painel">
      <header>
        <div>
          <h1>Painel Convertta</h1>
          <p className="sutil">
            {usuario === null ? "Leads e campanhas num lugar só." : `Olá, ${usuario.nome}.`}
            {atualizadoEm !== null && (
              <> Atualizado às {atualizadoEm.toLocaleTimeString("pt-BR").slice(0, 5)}.</>
            )}
          </p>
        </div>
        <div className="acoes-topo">
          <button onClick={() => setFormulario("lead")}>Novo</button>
          <button className="secundario" onClick={carregar} disabled={carregando}>
            {carregando && !primeiraCarga ? "Atualizando…" : "Atualizar"}
          </button>
          <button className="secundario" onClick={expirou}>
            Sair
          </button>
        </div>
      </header>

      <div className="filtro" role="group" aria-label="Período">
        {PRESETS.map((p) => (
          <button
            key={p.chave}
            type="button"
            className={`opcao ${preset === p.chave ? "ativa" : ""}`}
            aria-pressed={preset === p.chave}
            onClick={() => setPreset(p.chave)}
          >
            {p.rotulo}
          </button>
        ))}
      </div>

      {demorou && primeiraCarga && <AvisoDeDespertar />}
      {erro !== null && <Erro mensagem={erro} aoTentarDeNovo={carregar} />}
      {erro === null && primeiraCarga && carregando && <Esqueleto />}

      {visao !== null && (
        <div className={carregando ? "conteudo esmaecido" : "conteudo"}>
          <section className="numeros">
            <Numero
              rotulo="Investimento"
              valor={emReais(visao.resumo.investimento_centavos)}
              detalhe={preset === "tudo" ? "todo o histórico" : "rateado no período"}
            />
            <Numero
              rotulo="Campanhas"
              valor={emNumero(visao.resumo.campanhas)}
              detalhe={plural(visao.resumo.linhas.length, "cliente", "clientes")}
            />
            <Numero
              rotulo="Leads"
              valor={emNumero(visao.resumo.leads)}
              detalhe={plural(visao.resumo.leads_ganhos, "ganho", "ganhos")}
            />
            <Numero
              rotulo="Custo por lead"
              valor={emReais(visao.resumo.custo_por_lead_centavos)}
              detalhe={
                visao.resumo.custo_por_lead_centavos === null ? "sem leads ainda" : "média geral"
              }
            />
            <Numero
              rotulo="Conversão"
              valor={emPorcento(visao.resumo.taxa_conversao)}
              detalhe="leads que viraram venda"
            />
          </section>

          <section className="cartao-grafico">
            <h2>Leads por dia</h2>
            <SerieDeLeads serie={visao.serie} />
          </section>

          <div className="lado-a-lado">
            <section className="cartao-grafico">
              <h2>Investimento por canal</h2>
              <BarrasDeCanal canais={visao.canais} />
            </section>
            <section className="cartao-grafico">
              <h2>Onde os leads estão</h2>
              <FunilDeStatus funil={visao.funil} />
            </section>
          </div>

          <section className="cartao-grafico">
            <h2>Por cliente</h2>
            {linhas.length === 0 ? (
              <Vazio
                titulo="Nenhum cliente cadastrado ainda."
                detalhe="Cadastre o primeiro para o painel ter o que somar."
                acao={{ rotulo: "Novo cliente", aoClicar: () => setFormulario("cliente") }}
              />
            ) : (
              <table>
                <thead>
                  <tr>
                    {COLUNAS.map((c) => (
                      <th
                        key={c.chave}
                        className={c.numerica ? "num" : ""}
                        aria-sort={
                          ordem.coluna === c.chave
                            ? ordem.crescente
                              ? "ascending"
                              : "descending"
                            : "none"
                        }
                      >
                        <button type="button" onClick={() => ordenarPor(c.chave)}>
                          {c.rotulo}
                          {ordem.coluna === c.chave && (
                            <span aria-hidden="true">{ordem.crescente ? " ↑" : " ↓"}</span>
                          )}
                        </button>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {linhas.map((l) => (
                    <tr key={l.cliente_id}>
                      <td>
                        <button
                          type="button"
                          className="link"
                          onClick={() => setClienteAberto(l.cliente_id)}
                        >
                          {l.cliente}
                        </button>
                      </td>
                      <td className="num">{emNumero(l.campanhas)}</td>
                      <td className="num">{emReais(l.investimento_centavos)}</td>
                      <td className="num">
                        {emNumero(l.leads)}
                        {l.leads_ganhos > 0 && (
                          <span className="sutil"> · {plural(l.leads_ganhos, "ganho", "ganhos")}</span>
                        )}
                      </td>
                      <td className="num">{emReais(l.custo_por_lead_centavos)}</td>
                      <td className="num">{emPorcento(l.taxa_conversao)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>

          <p className="sutil rodape">
            Um traço no custo por lead significa campanha sem lead ainda — não custo zero. Clique
            no nome do cliente para ver campanha a campanha.
          </p>
        </div>
      )}

      {clienteAberto !== null && (
        <DetalheCliente
          clienteId={clienteAberto}
          periodo={periodo}
          aoFechar={() => setClienteAberto(null)}
          aoMudarDados={carregar}
          aoExpirar={expirou}
        />
      )}

      {formulario !== null && (
        <NovoRegistro
          abaInicial={formulario}
          aoFechar={() => setFormulario(null)}
          aoSalvar={carregar}
          aoExpirar={expirou}
        />
      )}
    </div>
  );
}
