# da Brand a Friend · Archivio delle puntate

Archivio pubblico di tutte le puntate del podcast, ordinate per tema, che si aggiorna da solo.

## Come funziona

Ogni lunedì GitHub fa tre cose, da solo:

1. legge il feed Spreaker e salva titolo, copertina, descrizione e audio di ogni puntata (`data/episodes.json`);
2. chiede a spoken.md la trascrizione delle puntate nuove e la salva in `transcripts/`;
3. ricostruisce il sito in `docs/`, che GitHub Pages pubblica.

Le categorie stanno in `data/categories.json`. I riassunti brevi in `data/summaries.json`.
Una puntata nuova compare subito nel sito. Finché non ha una categoria, si vede solo sotto "Tutte".

## La chiave di spoken.md

La chiave non va mai scritta nei file: il repository è pubblico.
Sta nei "secrets" di GitHub con il nome `SPOKEN_API_KEY`
(Settings → Secrets and variables → Actions).

## Trascrizioni

Per ora si usano solo dietro le quinte (temi, ricerca, riassunti).
Per mostrarle sul sito basta mettere `"show_transcripts": true` in `config.json`.

## Copia su robingood.com

La pagina vera dell'archivio è https://robingood.com/it/podcast/. Questa copia su GitHub resta come riserva e ha il tag canonical che punta a robingood.com.

- `scripts/deploy_pair.sh` manda la cartella `docs/` su pair.com, in `public_html/robingood_com/it/podcast/`.
- Lo lancia il job del lunedì (`aggiorna.yml`) dopo l'aggiornamento, e `robingood.yml` quando `docs/` cambia a mano.
- Servono i secrets `PAIR_SSH_KEY` (chiave privata dedicata a GitHub) e, se vuoi, `PAIR_KNOWN_HOSTS`. Senza chiave la copia viene saltata e il resto del job funziona come prima.
