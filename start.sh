#!/bin/bash
cd ~/MONARCH2026
echo "🚀 INICIANDO MONARCH2026©"
python bot_api.py &
python bot_voice.py &
wait
