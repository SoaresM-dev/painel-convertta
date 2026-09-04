/* Carregando, vazio e com erro — as três telas que ninguém desenha.
 *
 * **Esta é a tela que o recrutador vê primeiro, e por mais tempo.** O painel
 * roda no plano gratuito do Render, que hiberna o serviço depois de ~15 min
 * ocioso; o próprio provedor avisa que o acesso seguinte pode atrasar "50
 * segundos ou mais", e aqui ainda somam a migração e o seed no despertar. A
 * versão anterior mostrava a palavra "Carregando…" durante esse minuto
 * inteiro, sem explicar nada. Quem abre o link acha que quebrou e fecha a aba
 * — e o deploy inteiro deixa de valer alguma coisa por falta de uma frase.
 */
import { useEffect, useState } from "react";

/* Depois deste tempo, a espera deixa de ser normal e passa a merecer
 * explicação. Três segundos é curto o bastante para o aviso chegar antes da
 * dúvida, e longo o bastante para não piscar no carregamento comum. */
const MS_ATE_AVISAR = 3000;

export function useDemora(carregando: boolean): boolean {
  const [demorou, setDemorou] = useState(false);

  useEffect(() => {
    if (!carregando) {
      setDemorou(false);
      return;
    }
    const relogio = setTimeout(() => setDemorou(true), MS_ATE_AVISAR);
    return () => clearTimeout(relogio);
  }, [carregando]);

  return demorou;
}

export function AvisoDeDespertar() {
  return (
    <div className="despertar" role="status">
      <span className="girando" aria-hidden="true" />
      <div>
        <strong>Acordando o servidor.</strong>
        <p className="sutil">
          A API roda no plano gratuito do Render, que hiberna quando fica ociosa. O primeiro
          acesso leva até um minuto — os seguintes são instantâneos.
        </p>
      </div>
    </div>
  );
}

/* O esqueleto imita o formato final da tela, não um spinner genérico: quando
 * os dados chegam, nada salta de lugar. O `aria-hidden` existe porque para
 * quem usa leitor de tela isto é ruído — o `role="status"` do aviso já diz
 * que a página está carregando. */
export function Esqueleto() {
  return (
    <div className="esqueleto" aria-hidden="true">
      <div className="numeros">
        {[0, 1, 2, 3, 4].map((i) => (
          <div className="numero fantasma" key={i} />
        ))}
      </div>
      <div className="cartao-grafico fantasma alto" />
      <div className="lado-a-lado">
        <div className="cartao-grafico fantasma medio" />
        <div className="cartao-grafico fantasma medio" />
      </div>
      <div className="cartao-grafico fantasma alto" />
    </div>
  );
}

interface PropsErro {
  mensagem: string;
  aoTentarDeNovo: () => void;
}

export function Erro({ mensagem, aoTentarDeNovo }: PropsErro) {
  return (
    <div className="aviso-erro" role="alert">
      <strong>Não deu para carregar o painel.</strong>
      <p className="sutil">{mensagem}</p>
      <button className="secundario" onClick={aoTentarDeNovo}>
        Tentar de novo
      </button>
    </div>
  );
}

interface PropsVazio {
  titulo: string;
  detalhe: string;
  acao?: { rotulo: string; aoClicar: () => void };
}

export function Vazio({ titulo, detalhe, acao }: PropsVazio) {
  return (
    <div className="vazio">
      <strong>{titulo}</strong>
      <p className="sutil">{detalhe}</p>
      {acao !== undefined && <button onClick={acao.aoClicar}>{acao.rotulo}</button>}
    </div>
  );
}
