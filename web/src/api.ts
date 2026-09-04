/* Único lugar que fala com a API.
 *
 * Token no `sessionStorage` e não no `localStorage`: fechou a aba, acabou a
 * sessão — para uma ferramenta interna aberta em máquina de escritório, é o
 * padrão certo.
 */
import type {
  Campanha,
  Cliente,
  DetalheCliente,
  Funil,
  Lead,
  LinhaCanal,
  Resumo,
  Serie,
  StatusLead,
  Usuario,
  Visao,
} from "./tipos";

const BASE: string = import.meta.env.VITE_API ?? "http://localhost:8000";
const CHAVE = "painel_token";

export const token = {
  ler: (): string | null => sessionStorage.getItem(CHAVE),
  gravar: (t: string): void => sessionStorage.setItem(CHAVE, t),
  limpar: (): void => sessionStorage.removeItem(CHAVE),
};

/* Classe própria em vez de `Error` com uma flag: o `instanceof` no componente
 * distingue "expirou o token, volte para o login" de "deu erro, mostre a
 * mensagem" sem ninguém precisar comparar string. */
export class NaoAutorizado extends Error {}

/* O genérico é o que faz o TypeScript valer aqui: `pedir<Resumo>(...)` devolve
 * `Promise<Resumo>`, e daí em diante o compilador conhece cada campo. Sem ele
 * tudo isso seria `any` e o TypeScript viraria enfeite. */
async function pedir<T>(caminho: string, opcoes: RequestInit = {}): Promise<T> {
  const cabecalhos = new Headers(opcoes.headers);
  const t = token.ler();
  if (t !== null) cabecalhos.set("Authorization", `Bearer ${t}`);

  const resposta = await fetch(`${BASE}${caminho}`, { ...opcoes, headers: cabecalhos });

  /* 401 em qualquer chamada significa token expirado: limpa e devolve para o
   * login, em vez de deixar a tela quebrada com um erro genérico. */
  if (resposta.status === 401) {
    token.limpar();
    throw new NaoAutorizado("Sessão expirada");
  }
  if (!resposta.ok) {
    const corpo = (await resposta.json().catch(() => ({}))) as { detail?: unknown };
    throw new Error(mensagemDeErro(corpo.detail) ?? `Erro ${resposta.status}`);
  }
  /* 204 não tem corpo, e `resposta.json()` num corpo vazio estoura. É o que o
   * DELETE de cliente devolve. */
  if (resposta.status === 204) return undefined as T;
  return (await resposta.json()) as T;
}

/* O FastAPI devolve `detail` como string quando é um `HTTPException` nosso, e
 * como lista de objetos quando é o Pydantic recusando o corpo. Sem tratar os
 * dois, o segundo caso vira "[object Object]" na tela do usuário. */
function mensagemDeErro(detalhe: unknown): string | null {
  if (typeof detalhe === "string") return detalhe;
  if (Array.isArray(detalhe)) {
    const mensagens = detalhe
      .map((item) => (typeof item === "object" && item !== null && "msg" in item ? String(item.msg) : null))
      .filter((m): m is string => m !== null);
    if (mensagens.length > 0) return mensagens.join(". ");
  }
  return null;
}

function comCorpo(metodo: string, dados: unknown): RequestInit {
  return {
    method: metodo,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(dados),
  };
}

export async function entrar(email: string, senha: string): Promise<void> {
  const corpo = new URLSearchParams({ username: email, password: senha });
  const resposta = await fetch(`${BASE}/api/auth/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: corpo,
  });
  if (!resposta.ok) throw new Error("E-mail ou senha incorretos");
  const { access_token } = (await resposta.json()) as { access_token: string };
  token.gravar(access_token);
}

// --- período ---

export interface Periodo {
  de?: string;
  ate?: string;
}

function consulta(p: Periodo): string {
  const params = new URLSearchParams();
  if (p.de !== undefined) params.set("de", p.de);
  if (p.ate !== undefined) params.set("ate", p.ate);
  const texto = params.toString();
  return texto === "" ? "" : `?${texto}`;
}

/* `toISOString()` converteria para UTC antes de cortar a string, e em fuso
 * negativo isso devolve o dia anterior — o filtro de "hoje" começaria ontem
 * para quem está no Brasil. Montar a data a partir dos campos locais evita
 * a viagem por UTC. */
export function emISO(data: Date): string {
  const mes = `${data.getMonth() + 1}`.padStart(2, "0");
  const dia = `${data.getDate()}`.padStart(2, "0");
  return `${data.getFullYear()}-${mes}-${dia}`;
}

export function ultimosDias(dias: number): Periodo {
  const hoje = new Date();
  const inicio = new Date();
  inicio.setDate(hoje.getDate() - (dias - 1));
  return { de: emISO(inicio), ate: emISO(hoje) };
}

// --- as chamadas ---

export const api = {
  eu: () => pedir<Usuario>("/api/auth/eu"),

  resumo: (p: Periodo = {}) => pedir<Resumo>(`/api/painel/resumo${consulta(p)}`),
  canais: (p: Periodo = {}) => pedir<LinhaCanal[]>(`/api/painel/canais${consulta(p)}`),
  funil: (p: Periodo = {}) => pedir<Funil>(`/api/painel/funil${consulta(p)}`),
  serie: (p: Periodo = {}) => pedir<Serie>(`/api/painel/serie${consulta(p)}`),
  detalhe: (clienteId: number, p: Periodo = {}) =>
    pedir<DetalheCliente>(`/api/painel/clientes/${clienteId}${consulta(p)}`),

  /* As quatro visões numa espera só. Se qualquer uma falhar, a tela mostra o
   * erro inteiro em vez de meia página montada. */
  visao: async (p: Periodo = {}): Promise<Visao> => {
    const [resumo, canais, funil, serie] = await Promise.all([
      api.resumo(p),
      api.canais(p),
      api.funil(p),
      api.serie(p),
    ]);
    return { resumo, canais, funil, serie };
  },

  clientes: () => pedir<Cliente[]>("/api/clientes"),
  campanhas: () => pedir<Campanha[]>("/api/campanhas"),

  criarCliente: (nome: string) => pedir<Cliente>("/api/clientes", comCorpo("POST", { nome })),
  criarCampanha: (dados: {
    cliente_id: number;
    nome: string;
    canal: string;
    investimento_centavos: number;
    inicio: string;
    fim?: string;
  }) => pedir<Campanha>("/api/campanhas", comCorpo("POST", dados)),
  criarLead: (dados: {
    campanha_id: number;
    nome: string;
    email?: string;
    telefone?: string;
    status: StatusLead;
  }) => pedir<Lead>("/api/leads", comCorpo("POST", dados)),
  mudarStatus: (leadId: number, status: StatusLead) =>
    pedir<Lead>(`/api/leads/${leadId}`, comCorpo("PATCH", { status })),
};

// --- formatação, sempre na borda ---

/* Centavos -> "R$ 1.200,00". A conversão mora na borda: o resto do sistema só
 * conhece inteiro. `null` vira traço, nunca R$ 0,00 — zero leria como
 * "conseguimos leads de graça". */
export const emReais = (centavos: number | null): string =>
  centavos === null
    ? "—"
    : (centavos / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

/* Versão curta para eixo de gráfico e cartão apertado: R$ 7,4 mil. */
export const emReaisCurto = (centavos: number | null): string => {
  if (centavos === null) return "—";
  const reais = centavos / 100;
  if (Math.abs(reais) >= 1000) return `R$ ${(reais / 1000).toFixed(1).replace(".", ",")} mil`;
  return emReais(centavos);
};

export const emPorcento = (fracao: number | null): string =>
  fracao === null ? "—" : `${(fracao * 100).toFixed(1).replace(".", ",")}%`;

export const emNumero = (valor: number): string => valor.toLocaleString("pt-BR");

/* "1 lead", "2 leads". Concordância é acabamento, e acabamento é o que separa
 * ferramenta de exercício: "1 ganhos" é a primeira coisa que se lê numa tela,
 * antes até do número que ela existe para mostrar. */
export const plural = (quantidade: number, singular: string, plural: string): string =>
  `${emNumero(quantidade)} ${quantidade === 1 ? singular : plural}`;

/* `new Date("2026-08-13")` é interpretado como meia-noite **UTC**, e em fuso
 * negativo volta um dia: o gráfico mostraria 12/08 no ponto de 13/08. Por isso
 * a data do dia é fatiada como texto, sem passar por `Date`. */
export const emDiaMes = (iso: string): string => {
  const partes = iso.split("-");
  const mes = partes[1] ?? "";
  const dia = partes[2] ?? "";
  return `${dia}/${mes}`;
};

/* Aqui o `Date` é seguro: `criado_em` vem com fuso explícito no texto. */
export const emDataHora = (iso: string): string =>
  new Date(iso).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
