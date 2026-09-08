interface Props {
  /** Texto livre multilinha (decisao E1 da spec de edicao de perfil). */
  history: string | null;
}

/**
 * Historico de clubes do atleta. Campo exclusivo do atleta (scouts e clubes
 * nao tem esse dado), por isso vive fora do ProfileShell compartilhado.
 *
 * Quando vazio, o bloco inteiro e omitido em vez de mostrar um titulo sem
 * conteudo — o mesmo padrao ja usado para o selo de clube atual na pagina.
 * A quebra de linha e preservada via CSS (`white-space: pre-line`), nunca via
 * HTML: o atleta escreve um clube por linha e o texto e livre, entao marcacao
 * gerada a partir dele nao seria segura.
 */
export function ClubHistory({ history }: Props) {
  const trimmed = history?.trim();

  if (!trimmed) {
    return null;
  }

  return (
    <section className="profile-club-history">
      <h2>Histórico de Clubes</h2>
      <p>{history}</p>
    </section>
  );
}
