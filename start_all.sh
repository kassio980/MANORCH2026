#!/bin/bash
cd "$(dirname "$0")"
mkdir -p logs
echo "🏢 MONARCH FINANCE LTDA — INICIANDO SISTEMA COMPLETO"
echo "================================================"

# Site (só redirect)
pkill -f "node server.js" 2>/dev/null
nohup node server.js > logs/site.log 2>&1 &
echo "✅ SITE (redirect Discord)"

cd bots
for bot in bot_vendas.py bot_ticket.py bot_boasvindas.py bot_auth2.py bot_limpeza.py bot_gerador.py bot_emoji_tec.py bot_auth2_duplo.py bot_monarch_api_v8.py; do
  [ -f "$bot" ] || continue
  pkill -f "python3 $bot" 2>/dev/null
  nohup python3 -u "$bot" > "../logs/${bot%.py}.log" 2>&1 &
  echo "✅ $(echo ${bot%.py} | tr '[:lower:]' '[:upper:]')"
done

cd ..
echo ""
echo "🚀 TUDO NO AR!"
echo "📂 Logs em: logs/"
echo "🏢 MONARCH FINANCE LTDA"
