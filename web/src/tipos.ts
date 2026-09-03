/* O contrato da API, escrito uma vez.
 *
 * **Estes tipos espelham os schemas Pydantic do back-end.** É duplicação, e
 * duplicação consciente: gerar o cliente a partir do OpenAPI do FastAPI seria
 * a solução sem repetição, mas acrescenta um passo de build e uma dependência
 * a um projeto de três entidades. Enquanto o contrato couber numa tela, o
 * arquivo único é mais barato de ler do que de gerar.
 *
 * O que ele compra: se o back-end renomear `custo_por_lead_centavos`, o
 * `tsc` aponta a linha exata do componente que quebrou — em JavaScript, isso
 * apareceria como "—" na tela e ninguém notaria.
 */

export type Canal = "google_ads" | "meta_ads";

export type StatusLead =
  | "novo"
  | "contatado"
  | "qualificado"
  | "ganho"
  | "perdido";

export interface Usuario {
  id: number;
  email: string;
  nome: string;
}

export interface Cliente {
  id: number;
  nome: string;
  criado_em: string;
}

export interface Campanha {
  id: number;
  cliente_id: number;
  nome: string;
  canal: Canal;
  investimento_centavos: number;
  inicio: string;
  fim: string | null;
}

export interface Lead {
  id: number;
  campanha_id: number;
  nome: string;
  email: string | null;
  telefone: string | null;
  status: StatusLead;
  criado_em: string;
}

/* `| null` e não `?`: a API SEMPRE manda o campo, e o valor é null quando a
 * campanha ainda não trouxe lead nenhum. Marcar como opcional deixaria o
 * `undefined` passar e esconderia a diferença entre "não veio" e "não dá para
 * saber ainda" — que é justamente a distinção que este painel faz questão de
 * mostrar. */
export interface LinhaResumo {
  cliente_id: number;
  cliente: string;
  campanhas: number;
  investimento_centavos: number;
  leads: number;
  leads_ganhos: number;
  custo_por_lead_centavos: number | null;
  taxa_conversao: number | null;
}

export interface Resumo {
  investimento_centavos: number;
  leads: number;
  leads_ganhos: number;
  custo_por_lead_centavos: number | null;
  linhas: LinhaResumo[];
}
