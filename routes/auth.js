const express = require('express');
const router = express.Router();
const axios = require('axios');
const db = require('../db');

const DC_ID     = process.env.DISCORD_CLIENT_ID;
const DC_SECRET = process.env.DISCORD_CLIENT_SECRET;
const ID_DONO   = String(process.env.ID_DONO_DISCORD || '0');

const redirectUri = (host) => `https://${host}/auth/discord/callback`;

router.get('/discord', (req, res) => {
  if (!DC_ID || !DC_SECRET) return res.send('❌ Configure DISCORD_CLIENT_ID e DISCORD_CLIENT_SECRET no Render.');
  const host = (req.get('host')||'bot-machion-all.onrender.com').replace(/:\d+$/,'');
  req.session._host = host;
  res.redirect(`https://discord.com/api/oauth2/authorize?client_id=${DC_ID}&redirect_uri=${encodeURIComponent(redirectUri(host))}&response_type=code&scope=${encodeURIComponent('identify email')}&prompt=consent`);
});

router.get('/discord/callback', async (req, res) => {
  try {
    const {code} = req.query; if(!code) return res.redirect('/login?erro=1');
    const host = req.session._host || 'bot-machion-all.onrender.com';
    const tok = await axios.post('https://discord.com/api/oauth2/token', new URLSearchParams({
      client_id:DC_ID, client_secret:DC_SECRET, grant_type:'authorization_code', code, redirect_uri:redirectUri(host)
    }), {headers:{'Content-Type':'application/x-www-form-urlencoded'}});
    const eu = await axios.get('https://discord.com/api/users/@me', {headers:{Authorization:`Bearer ${tok.data.access_token}`}});
    const usuario = db.salvarUsuario({
      discordId: eu.data.id,
      username: `${eu.data.username}${eu.data.discriminator&&eu.data.discriminator!=='0'?'#'+eu.data.discriminator:''}`,
      avatar: eu.data.avatar, email: eu.data.email,
      // ✅ É dono SE o ID Discord bater com a variável ID_DONO_DISCORD
      isDono: eu.data.id === ID_DONO
    });
    req.session.user = usuario;
    db.log(usuario.username, 'LOGIN_DISCORD', req.ip);
    const volta = req.session.volta; delete req.session.volta;
    if (volta) return res.redirect(volta);
    // ✅ Se for dono vai pro painel dono, senão pro painel usuário
    return res.redirect(usuario.is_dono_plataforma === 1 ? '/dono' : '/painel');
  } catch(e){ console.error('AUTH ERRO:',e.response?.data||e.message); res.redirect('/login?erro=2'); }
});

router.get('/sair', (req, res) => req.session.destroy(()=>res.redirect('/login')));
module.exports = router;
