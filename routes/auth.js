const express = require('express');
const router = express.Router();
const axios = require('axios');
const db = require('../db');

const DC_ID     = process.env.DISCORD_CLIENT_ID;
const DC_SECRET = process.env.DISCORD_CLIENT_SECRET;
const DC_BOT    = process.env.DISCORD_BOT_TOKEN;
const ID_DONO   = String(process.env.ID_DONO_DISCORD || '0');
const SRV_ID    = process.env.SERVIDOR_MEMBROS_ID || db.cfg().servidor_id;
const REDIRECT  = host => `https://${host}/auth/discord/callback`;
const SCOPES    = 'identify email guilds guilds.join';

router.get('/discord', (req, res) => {
  if (!DC_ID || !DC_SECRET) return res.send(`
    <div style="font-family:Arial;padding:40px;max-width:600px;margin:50px auto;background:#111;color:#fff;border-radius:16px">
      <h2 style="color:#ef4444">❌ Faltam variáveis no Render</h2>
      <p>Adicione essas 2 variáveis em <b>Environment</b>:</p>
      <pre style="background:#000;padding:14px;border-radius:8px">DISCORD_CLIENT_ID=SEU_ID<br>DISCORD_CLIENT_SECRET=SEU_SEGREDO</pre>
      <p style="color:#a78bfa">URL Redirect no Discord Developer:</p>
      <code style="background:#000;padding:8px">https://bot-machion-all.onrender.com/auth/discord/callback</code>
    </div>`);
  const host = (req.get('host')||'bot-machion-all.onrender.com').replace(/:\d+$/,'');
  req.session._host = host;
  res.redirect(`https://discord.com/api/oauth2/authorize?client_id=${DC_ID}&redirect_uri=${encodeURIComponent(REDIRECT(host))}&response_type=code&scope=${encodeURIComponent(SCOPES)}&prompt=consent`);
});

router.get('/discord/callback', async (req, res) => {
  try {
    const {code} = req.query; if(!code) return res.redirect('/login?erro=1');
    const host = req.session._host || 'bot-machion-all.onrender.com';
    const tok = await axios.post('https://discord.com/api/oauth2/token', new URLSearchParams({
      client_id:DC_ID, client_secret:DC_SECRET, grant_type:'authorization_code', code, redirect_uri:REDIRECT(host)
    }), {headers:{'Content-Type':'application/x-www-form-urlencoded'}});
    const eu = await axios.get('https://discord.com/api/users/@me', {headers:{Authorization:`Bearer ${tok.data.access_token}`}});

    // ✅ Verifica se já entrou no servidor obrigatório
    let entrou = 0;
    if (SRV_ID && DC_BOT) {
      try {
        await axios.get(`https://discord.com/api/guilds/${SRV_ID}/members/${eu.data.id}`, {headers:{Authorization:`Bot ${DC_BOT}`}});
        entrou = 1;
      } catch(e){ entrou = 0; }
    }

    const usuario = db.salvarUsuario({
      discordId: eu.data.id,
      username: `${eu.data.username}${eu.data.discriminator&&eu.data.discriminator!=='0'?'#'+eu.data.discriminator:''}`,
      avatar: eu.data.avatar, email: eu.data.email,
      isDono: eu.data.id === ID_DONO
    });
    db.db.prepare('UPDATE usuarios SET entrou_servidor=? WHERE id=?').run(entrou, usuario.id);
    req.session.user = usuario;
    const volta = req.session.volta; delete req.session.volta;
    if (volta) return res.redirect(volta);
    return res.redirect(usuario.is_dono_plataforma === 1 ? '/dono' : '/painel');
  } catch(e){ console.error('AUTH:',e.response?.data||e.message); res.redirect('/login?erro=2'); }
});

router.get('/sair', (req, res) => req.session.destroy(()=>res.redirect('/login')));
module.exports = router;
