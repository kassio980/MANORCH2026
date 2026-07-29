#!/bin/bash
cd ~/MONARCH2026
echo "══════════════════════════════════"
echo "👑 TESTE COMPLETO MONARCH2026"
echo "══════════════════════════════════"

OK=0
echo -e "\n🔍 TESTANDO ARQUIVOS PYTHON:"
for arq in templates/bot_basico.py templates/bot_intermediario.py templates/bot_vip.py templates/bot_premium.py; do
  if [ -f "$arq" ]; then
    echo -n "✅ $arq "
    if python3 -m py_compile "$arq" 2>/dev/null; then
      echo "🟢 SINTAXE OK"
    else
      echo "🔴 ERRO!"
      python3 -m py_compile "$arq"
      OK=1
    fi
  else
    echo "❌ $arq NAO EXISTE"
    OK=1
  fi
done

echo -e "\n🔍 VERIFICANDO ARQUIVOS ESSENCIAIS:"
for f in server.js package.json .env Procfile; do
  [ -f "$f" ] && echo "✅ $f EXISTE" || echo "⚠️ $f NAO ENCONTRADO"
done

echo -e "\n🔍 DEPENDENCIAS NODE:"
[ -d "node_modules" ] && echo "✅ node_modules OK" || echo "⚠️ node_modules nao encontrado"

echo -e "\n══════════════════════════════════"
if [ $OK -eq 0 ]; then
  echo "✅ TUDO PERFEITO! PODE ENVIAR PRO GITHUB"
else
  echo "⚠️ TEM ERROS — CORRIJA ANTES"
fi
echo "══════════════════════════════════"
