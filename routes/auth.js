const express = require('express');
const router = express.Router();
const axios = require('axios');
const db = require('../db');

const DC = {
  id: process.env.DISCORD_CLIENT_ID,
  secret: process.env.DISCORD_CLIENT_SECRET,
  redirect: process.env.DISCORD_REDIRECT || 'http://localhost:3000/auth/callback',
  escopo: 'identify email guilds'
};

router.get('/discord', (req, res) => res.redirect(
  `https://discord.com/api/oauth2/authorize?client_id=${DC.id}&redirect_uri=${encodeURIComponent(DC.redirect)}&response_type=code&scope=${encodeURIComponent(DC.escopo)}`
));

router.get('/callback', async (req, res) => {
  try {
    const {code} = req.query; if(!code) return res.redirect('/login?erro=1');
    const tok = await axios.post('https://discord.com/api/oauth2/token', new URLSearchParams({
      client_id:DC.id, client_secret:DC.secret, grant_type:'authorization_code', code, redirect_uri:DC.redirect
    }), {headers:{'Content-Type':'application/x-www-form-urlencoded'}});
    const eu = await axios.get('https://discord.com/api/users/@me', {headers:{Authorization:`Bearer ${tok.data.access_token}`}});
    const usuario = db.salvarUsuario({
      discordId: eu.data.id,
      username: `${eu.data.username}${eu.data.discriminator&&eu.data.discriminator!=='0'?'#'+eu.data.discriminator:''}`,
      avatar: eu.data.avatar, email: eu.data.email,
      isDono: eu.data.id === String(process.env.ID_DONO_DISCORD)
    });
    req.session.user = usuario;
    db.log(usuario.username, 'LOGIN_DISCORD', req.ip);
    return res.redirect(usuario.is_dono?'/dono':'/painel');
  } catch(e){ console.error('AUTH ERRO:',e); res.redirect('/login?erro=2'); }
});

router.get('/sair', (req, res) => {
  if(req.session.user) db.log(req.session.user.username,'LOGOUT',req.ip);
  req.session.destroy(()=>res.redirect('/'));
});
module.exports = router;
