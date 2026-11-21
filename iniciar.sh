#!/bin/sh
cd "$(dirname "$0")"
command -v node >/dev/null || { echo "Node.js não encontrado. Instale a versão LTS em https://nodejs.org"; exit 1; }
[ -d node_modules ] || npm install || exit 1
(sleep 1; (open http://localhost:3000/mestre || xdg-open http://localhost:3000/mestre) >/dev/null 2>&1) &
node server.js
