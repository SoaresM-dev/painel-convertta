/* Os gráficos, em SVG escrito à mão.
 *
 * **Por que não uma biblioteca.** Recharts resolveria isto em menos linhas e
 * custaria ~100 kB comprimidos — mais que todo o resto do bundle junto, num
 * projeto de três entidades e três gráficos. O que se ganha com ela (zoom,
 * pan, eixos configuráveis, dezenas de tipos de série) nenhuma destas telas
 * usa. É a mesma decisão registrada em `tipos.ts` sobre não gerar o cliente a
 * partir do OpenAPI: enquanto couber numa tela, escrever é mais barato do que
 * depender.
 *
 * O `viewBox` fixo com `width: 100%` é o que faz os três serem responsivos
 * sem `ResizeObserver` e sem medir nada em JavaScript: o navegador escala o
 * desenho inteiro, e as proporções que eu escolhi sobrevivem em qualquer
 * largura.
 */
import { useState } from "react";
import { emDiaMes, emPorcento, emReais, plural } from "./api";
import type { Funil, LinhaCanal, PontoSerie, Serie } from "./tipos";
import { ROTULO_CANAL, ROTULO_STATUS } from "./tipos";

// --- série temporal ---

const LARGURA = 720;
const ALTURA = 190;
const MARGEM = { topo: 14, direita: 10, baixo: 24, esquerda: 38 };
const UTIL_X = LARGURA - MARGEM.esquerda - MARGEM.direita;
const UTIL_Y = ALTURA - MARGEM.topo - MARGEM.baixo;

interface PropsSerie {
  serie: Serie;
}

export function SerieDeLeads({ serie }: PropsSerie) {
  const [ativo, setAtivo] = useState<number | null>(null);
  const pontos = serie.pontos;

  if (pontos.length === 0) {
    return <VazioDoGrafico mensagem="Nenhum lead neste período." />;
  }

  /* O teto é o maior valor, nunca menos que 1: com todos os dias em zero, uma
   * escala de 0 a 0 dividiria por zero e sumiria com a linha. */
  const teto = Math.max(1, ...pontos.map((p) => p.leads));
  const passo = Math.max(pontos.length - 1, 1);

  const x = (i: number): number => MARGEM.esquerda + (i / passo) * UTIL_X;
  const y = (valor: number): number => MARGEM.topo + (1 - valor / teto) * UTIL_Y;
  const base = MARGEM.topo + UTIL_Y;

  const linha = (pegar: (p: PontoSerie) => number): string =>
    pontos.map((p, i) => `${i === 0 ? "M" : "L"} ${x(i)} ${y(pegar(p))}`).join(" ");

  const area = `${linha((p) => p.leads)} L ${x(pontos.length - 1)} ${base} L ${x(0)} ${base} Z`;

  /* Três marcas no eixo vertical bastam para dar escala. Mais que isso vira
   * grade, e grade rouba atenção da linha, que é o que importa aqui. */
  const marcas = [0, Math.round(teto / 2), teto].filter(
    (valor, indice, todas) => todas.indexOf(valor) === indice
  );

  const destacado = ativo === null ? undefined : pontos[ativo];

  return (
    <div className="grafico" onMouseLeave={() => setAtivo(null)}>
      <svg
        viewBox={`0 0 ${LARGURA} ${ALTURA}`}
        className="tela"
        role="img"
        aria-label={`Leads por dia, de ${emDiaMes(pontos[0]?.dia ?? "")} a ${emDiaMes(
          pontos[pontos.length - 1]?.dia ?? ""
        )}`}
      >
        <defs>
          <linearGradient id="preenchimento-leads" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--destaque)" stopOpacity="0.28" />
            <stop offset="100%" stopColor="var(--destaque)" stopOpacity="0" />
          </linearGradient>
        </defs>

        {marcas.map((valor) => (
          <g key={valor}>
            <line
              x1={MARGEM.esquerda}
              x2={LARGURA - MARGEM.direita}
              y1={y(valor)}
              y2={y(valor)}
              className="grade"
            />
            <text x={MARGEM.esquerda - 8} y={y(valor) + 4} className="marca fim">
              {valor}
            </text>
          </g>
        ))}

        <path d={area} fill="url(#preenchimento-leads)" />
        <path d={linha((p) => p.leads)} className="traco leads" />
        <path d={linha((p) => p.leads_ganhos)} className="traco ganhos" />

        {destacado !== undefined && ativo !== null && (
          <>
            <line x1={x(ativo)} x2={x(ativo)} y1={MARGEM.topo} y2={base} className="guia" />
            <circle cx={x(ativo)} cy={y(destacado.leads)} r="4" className="ponto leads" />
            <circle cx={x(ativo)} cy={y(destacado.leads_ganhos)} r="3" className="ponto ganhos" />
          </>
        )}

        <text x={MARGEM.esquerda} y={ALTURA - 6} className="marca">
          {emDiaMes(pontos[0]?.dia ?? "")}
        </text>
        <text x={LARGURA - MARGEM.direita} y={ALTURA - 6} className="marca fim">
          {emDiaMes(pontos[pontos.length - 1]?.dia ?? "")}
        </text>

        {/* A faixa invisível é o alvo do mouse. Sem ela, acertar uma linha de
            dois pixels com o cursor seria um exercício de pontaria. */}
        {pontos.map((p, i) => (
          <rect
            key={p.dia}
            x={x(i) - UTIL_X / passo / 2}
            y={MARGEM.topo}
            width={UTIL_X / passo}
            height={UTIL_Y}
            fill="transparent"
            onMouseEnter={() => setAtivo(i)}
          />
        ))}
      </svg>

      {destacado !== undefined && ativo !== null && (
        <div
          className="dica"
          style={{ left: `${(x(ativo) / LARGURA) * 100}%` }}
          data-lado={ativo > pontos.length / 2 ? "esquerda" : "direita"}
        >
          <strong>{emDiaMes(destacado.dia)}</strong>
          <span>{plural(destacado.leads, "lead", "leads")}</span>
          <span className="sutil">{plural(destacado.leads_ganhos, "ganho", "ganhos")}</span>
        </div>
      )}

      <div className="legenda">
        <span className="chave leads">Leads</span>
        <span className="chave ganhos">Ganhos</span>
      </div>
    </div>
  );
}

// --- canais ---

interface PropsCanais {
  canais: LinhaCanal[];
}

export function BarrasDeCanal({ canais }: PropsCanais) {
  const teto = Math.max(1, ...canais.map((c) => c.investimento_centavos));
  const semDado = canais.every((c) => c.investimento_centavos === 0 && c.leads === 0);

  if (semDado) return <VazioDoGrafico mensagem="Nenhuma campanha neste período." />;

  /* O canal mais barato ganha destaque, e só quando os dois têm custo: com um
   * canal só, "o mais barato" não é comparação, é tautologia. */
  const comCusto = canais.filter((c) => c.custo_por_lead_centavos !== null);
  const melhor =
    comCusto.length < 2
      ? null
      : comCusto.reduce((a, b) =>
          (a.custo_por_lead_centavos ?? 0) <= (b.custo_por_lead_centavos ?? 0) ? a : b
        ).canal;

  return (
    <div className="canais">
      {canais.map((c) => (
        <div className="canal" key={c.canal}>
          <div className="canal-topo">
            <span className="canal-nome">
              {ROTULO_CANAL[c.canal]}
              {melhor === c.canal && <em className="selo">lead mais barato</em>}
            </span>
            <span className="num">{emReais(c.investimento_centavos)}</span>
          </div>
          <div className="barra" role="presentation">
            <div
              className={`preenchimento ${c.canal}`}
              style={{ width: `${(c.investimento_centavos / teto) * 100}%` }}
            />
          </div>
          <div className="canal-rodape sutil">
            <span>{plural(c.leads, "lead", "leads")}</span>
            <span>{emReais(c.custo_por_lead_centavos)} por lead</span>
            <span>{emPorcento(c.taxa_conversao)} de conversão</span>
          </div>
        </div>
      ))}
    </div>
  );
}

// --- funil ---

interface PropsFunil {
  funil: Funil;
}

export function FunilDeStatus({ funil }: PropsFunil) {
  if (funil.total === 0) return <VazioDoGrafico mensagem="Nenhum lead neste período." />;

  const teto = Math.max(1, ...funil.estagios.map((e) => e.leads));

  return (
    <div className="funil">
      {funil.estagios.map((e) => (
        <div className={`degrau ${e.status}`} key={e.status}>
          <span className="degrau-nome">{ROTULO_STATUS[e.status]}</span>
          <div className="barra">
            <div className="preenchimento" style={{ width: `${(e.leads / teto) * 100}%` }} />
          </div>
          <span className="num degrau-valor">
            {e.leads}
            <span className="sutil"> · {emPorcento(e.leads / funil.total)}</span>
          </span>
        </div>
      ))}
      <p className="sutil nota">
        Distribuição por estágio, não funil cumulativo: o banco guarda onde o lead{" "}
        <strong>está</strong>, não por onde passou.
      </p>
    </div>
  );
}

// --- o vazio, uma vez só ---

function VazioDoGrafico({ mensagem }: { mensagem: string }) {
  return <p className="sutil vazio-grafico">{mensagem}</p>;
}
