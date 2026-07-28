const express = require('express');
const router = express.Router();
router.get('/status/:id', (req,res)=>res.json({id:req.params.id,status:'ONLINE',cpu:(Math.random()*20+3).toFixed(1),ram:(Math.random()*300+64).toFixed(0)+' MB',uptime:'14d 08h'}));
module.exports = router;
