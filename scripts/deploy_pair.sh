#!/bin/bash
# Copia la cartella docs/ su robingood.com/it/podcast/ (server pair.com).
# Gira dentro GitHub Actions. Serve il secret PAIR_SSH_KEY (chiave privata).
# PAIR_KNOWN_HOSTS e' facoltativo: se manca, la chiave del server viene letta al volo.
set -euo pipefail

HOST="robingood@robingood.pairserver.com"
DEST="public_html/robingood_com/it/podcast"
URL="https://robingood.com/it/podcast/"

if [ -z "${PAIR_SSH_KEY:-}" ]; then
  echo "PAIR_SSH_KEY non c'e' nei secrets: salto la copia su robingood.com."
  exit 0
fi

mkdir -p ~/.ssh && chmod 700 ~/.ssh
printf '%s\n' "$PAIR_SSH_KEY" > ~/.ssh/pair_key
chmod 600 ~/.ssh/pair_key
if [ -n "${PAIR_KNOWN_HOSTS:-}" ]; then
  printf '%s\n' "$PAIR_KNOWN_HOSTS" > ~/.ssh/known_hosts
else
  ssh-keyscan -t ed25519,rsa robingood.pairserver.com > ~/.ssh/known_hosts 2>/dev/null
fi

SSH=(ssh -i ~/.ssh/pair_key -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes)

# Pair apre una shell csh, quindi i comandi passano da bash -c (come in "Deploy to Pair.command").
COPYFILE_DISABLE=1 tar cf - --exclude='.nojekyll' --exclude='./covers/README.md' -C docs . \
  | "${SSH[@]}" "$HOST" "bash -c 'mkdir -p ~/$DEST && cd ~/$DEST && tar xf - --no-same-owner && find . -type d -exec chmod 755 {} + && find . -type f -exec chmod 644 {} +'"

rm -f ~/.ssh/pair_key

CODE=$(curl -s -o /dev/null -w '%{http_code}' "$URL")
echo "robingood.com/it/podcast/ risponde: $CODE"
[ "$CODE" = "200" ] || { echo "La pagina non risponde 200. Controlla."; exit 1; }
