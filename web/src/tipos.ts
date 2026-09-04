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
  campanhas: number;
  leads: number;
  leads_ganhos: number;
  custo_por_lead_centavos: number | null;
  taxa_conversao: number | null;
  linhas: LinhaResumo[];
}

export interface LinhaCanal {
  canal: Canal;
  campanhas: number;
  investimento_centavos: number;
  leads: number;
  leads_ganhos: number;
  custo_por_lead_centavos: number | null;
  taxa_conversao: number | null;
}

export interface EstagioFunil {
  status: StatusLead;
  leads: number;
}

export interface Funil {
  total: number;
  estagios: EstagioFunil[];
}

export interface PontoSerie {
  dia: string;
  leads: number;
  leads_ganhos: number;
}

export interface Serie {
  pontos: PontoSerie[];
}

export interface CampanhaDetalhe {
  id: number;
  nome: string;
  canal: Canal;
  investimento_centavos: number;
  inicio: string;
  fim: string | null;
  leads: number;
  leads_ganhos: number;
  custo_por_lead_centavos: number | null;
  taxa_conversao: number | null;
}

export interface LeadRecente {
  id: number;
  nome: string;
  email: string | null;
  telefone: string | null;
  status: StatusLead;
  criado_em: string;
  campanha_id: number;
  campanha: string;
}

export interface DetalheCliente {
  cliente_id: number;
  cliente: string;
  campanhas: CampanhaDetalhe[];
  leads_recentes: LeadRecente[];
}

/* Tudo o que o painel carrega de uma vez. Um `Promise.all` no lugar de quatro
 * carregamentos independentes: no plano gratuito do Render a primeira chamada
 * paga o despertar do serviço, e quatro espinhas de "carregando" acendendo em
 * momentos diferentes fazem a tela parecer quebrada. */
export interface Visao {
  resumo: Resumo;
  canais: LinhaCanal[];
  funil: Funil;
  serie: Serie;
}

export const ROTULO_CANAL: Record<Canal, string> = {
  google_ads: "Google Ads",
  meta_ads: "Meta Ads",
};

export const ROTULO_STATUS: Record<StatusLead, string> = {
  novo: "Novo",
  contatado: "Contatado",
  qualificado: "Qualificado",
  ganho: "Ganho",
  perdido: "Perdido",
};
