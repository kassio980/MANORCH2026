const express = require('express');
const router = express.Router();
const axios = require('axios');
const db = require('../db');

const DC = {
  id: process.env.DISCORD_CLIENT_ID,
  secret: process.env.DISCORD_CLIENT_SECRET,
  // ✅ Aceita QUALQUER um dos 3 domínios automaticamente
  redirect: (host) => `https://${host}/auth/discord/callback`,
  escopo: 'identify email guilds'
};

router.get('/discord', (req, res) => {
  const host = (req.get('host')||'bot-machion-all.onrender.com').replace(/:\d+$/,'');
  req.session._host = host;
  res.redirect(
    `https://discord.com/api/oauth2/authorize?client_id=${DC.id}&redirect_uri=${encodeURIComponent(DC.redirect(host))}&response_type=code&scope=${encodeURIComponent(DC.escopo)}&prompt=none`
  );
});

router.get('/discord/callback', async (req, res) => {
  try {
    const {code} = req.query; if(!code) return res.redirect('/login?erro=1');
    const host = req.session._host || 'bot-machion-all.onrender.com';
    const tok = await axios.post('https://discord.com/api/oauth2/token', new URLSearchParams({
      client_id:DC.id, client_secret:DC.secret, grant_type:'authorization_code', code, redirect_uri:DC.redirect(host)
    }), {headers:{'Content-Type':'application/x-www-form-urlencoded'}});
    const eu = await axios.get('https://discord.com/api/users/@me', {headers:{Authorization:`Bearer ${tok.data.access_token}`}});
    const usuario = db.salvarUsuario({
      discordId: eu.data.id,
      username: `${eu.data.username}${eu.data.discriminator&&eu.data.discriminator!=='0'?'#'+eu.data.discriminator:''}`,
      avatar: eu.data.avatar, email: eu.data.email,
      // ✅ Se logar pelo domínio DONO, já marca como dono se for o seu ID
      isDono: host.includes('dono-painel') || eu.data.id === String(process.env.ID_DONO_DISCORD||'0')
    });
    req.session.user = usuario;
    db.log(usuario.username, 'LOGIN', req.ip);
    // ✅ Volta pro lugar que ele estava, ou pro domínio certo
    const volta = req.session.volta;
    delete req.session.volta;
    if (volta) return res.redirect(volta);
    if (host.includes('dono-painel')) return res.redirect('https://dono-painel.onrender.com/dono');
    if (host.includes('api-vendas-manocrh')) return res.redirect('https://api-vendas-manocrh.onrender.com/painel');
    return res.redirect(usuario.is_dono_plataforma?'/dono':'/painel');
  } catch(e){ console.error('AUTH:',e); res.redirect('/login?erro=2'); }
});

router.get('/sair', (req, res) => {
  req.session.destroy(()=>res.redirect('/'));
});
module.exports = router;
