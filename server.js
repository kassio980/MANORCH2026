require('dotenv').config()
const express = require('express')
const app = express()
const PORT = process.env.PORT || 10000

// ==============================
// 🔐 SÓ REDIRECIONA PARA O DISCORD
// ==============================
app.get('/', (req, res) => {
  res.redirect('https://discord.gg/9jPnRdMbgp')
})

app.get('/convite', (req, res) => {
  res.redirect(process.env.SERVIDOR_CONVITE || 'https://discord.gg/9jPnRdMbgp')
})

// ==============================
// ✅ SAÚDE DO SISTEMA
// ==============================
app.get('/health', (req, res) => {
  res.json({ status: 'ONLINE', sistema: 'MONARCH API V8', empresa: 'MONARCH FINANCE LTDA' })
})

// ==============================
// 🚫 QUALQUER OUTRA ROTA → VAI PRO DISCORD
// ==============================
app.all('*', (req, res) => {
  res.redirect('/')
})

app.listen(PORT, () => {
  console.log(`✅ MONARCH API V8 | PORTA: ${PORT} | SÓ DISCORD`)
})
