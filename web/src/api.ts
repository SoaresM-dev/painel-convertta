/* Único lugar que fala com a API.
 *
 * Token no `sessionStorage` e não no `localStorage`: fechou a aba, acabou a
 * sessão — para uma ferramenta interna aberta em máquina de escritório, é o
 * padrão certo.
 */
import type { Resumo, Usuario } from "./tipos";

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
    const corpo = (await resposta.json().catch(() => ({}))) as { detail?: string };
    throw new Error(corpo.detail ?? `Erro ${resposta.status}`);
  }
  return (await resposta.json()) as T;
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

export const api = {
  eu: () => pedir<Usuario>("/api/auth/eu"),
  resumo: () => pedir<Resumo>("/api/painel/resumo"),
};

/* Centavos -> "R$ 1.200,00". A conversão mora na borda: o resto do sistema só
 * conhece inteiro. `null` vira traço, nunca R$ 0,00 — zero leria como
 * "conseguimos leads de graça". */
export const emReais = (centavos: number | null): string =>
  centavos === null
    ? "—"
    : (centavos / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

export const emPorcento = (fracao: number | null): string =>
  fracao === null ? "—" : `${(fracao * 100).toFixed(1).replace(".", ",")}%`;
