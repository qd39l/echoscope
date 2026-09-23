'use strict';
const M = window.EchoModel;
const $ = id => document.getElementById(id);
let world = M.initial(), generation = 0, mode = 0, audioContext, oscillator, gain;
const canvas = $('screen'), ctx = canvas.getContext('2d');
function draw() {
  ctx.fillStyle = '#000'; ctx.fillRect(0,0,640,480);
  let row = world;
  const diff = $('diff').checked;
  for (let y=0;y<60;y++) {
    for(let i=0;i<32;i++) {
      const a=(row[1]>>>i)&1,b=(row[3]>>>i)&1;
      ctx.fillStyle='#000055';ctx.fillRect(64+i*16,y*8,16,8);
      ctx.fillStyle=diff ? (a!==b?'#ffaa55':'#000') : (a?(b?'#fff':'#0ff'):(b?'#f0f':'#000'));
      ctx.fillRect(65+i*16,y*8,15,7);
    }
    row=M.step(row);
  }
  ctx.fillStyle=mode<0?'#f00':mode>0?'#0f0':'#0ff';
  ctx.fillRect(56,0,4,480);ctx.fillRect(580,0,4,480);
  for(let i=0;i<16;i++)if((generation>>>i)&1){ctx.fillStyle='#aaa';ctx.fillRect(24,i*16,16,12);}
  ctx.fillStyle='#ff5500';ctx.fillRect(600,0,16,M.distance(world)*8);
  $('epoch').textContent=(generation<0?'−':'+')+String(Math.abs(generation)).padStart(5,'0');
  $('distance').innerHTML=String(M.distance(world)).padStart(2,'0')+' <small>/ 32</small>';
  $('direction').textContent=mode<0?'REWINDING':mode>0?'FORWARD':'PAUSED';
  for(const [id,n] of [['reverse',-1],['pause',0],['forward',1]]){
    $(id).classList.toggle('selected',mode===n);$(id).setAttribute('aria-pressed',String(mode===n));
  }
  updateSound();
}
function tick(reverse){world=M.step(world,reverse);generation+=reverse?-1:1;draw();}
function stop(){mode=0;draw();}
function announce(text){$('announcement').textContent=text;}
$('back').onclick=()=>{stop();tick(true);announce('Stepped backward to generation '+generation);};
$('next').onclick=()=>{stop();tick(false);announce('Stepped forward to generation '+generation);};
$('reverse').onclick=()=>{mode=-1;draw();};$('forward').onclick=()=>{mode=1;draw();};$('pause').onclick=stop;
$('kick').onclick=()=>{world=M.kick(world,+$('cell').value);draw();announce('Flipped cell '+$('cell').value);};
$('clone').onclick=()=>{world=M.clone(world);draw();announce('Both worlds are now identical');};
$('reset').onclick=()=>{world=M.initial();generation=0;mode=0;draw();announce('Experiment restarted');};
$('cell').oninput=()=>{$('cell-value').textContent=$('cell').value;};$('diff').onchange=draw;
$('sound').onchange=async()=>{
  if($('sound').checked&&!audioContext){
    audioContext=new (window.AudioContext||window.webkitAudioContext)();
    oscillator=audioContext.createOscillator();oscillator.type='square';
    gain=audioContext.createGain();gain.gain.value=0;
    oscillator.connect(gain).connect(audioContext.destination);oscillator.start();
  }
  if(audioContext)await audioContext.resume();updateSound();
};
function updateSound(){if(!audioContext)return;const d=M.distance(world),p=[88,99,111,132,148,176,197,221][(d>>>2)&7];oscillator.frequency.setTargetAtTime(25000000*p/8388608,audioContext.currentTime,.01);gain.gain.setTargetAtTime($('sound').checked&&d?.025:0,audioContext.currentTime,.01);}
// Slowed to 12 generations/s for inspection; silicon advances at frame rate.
setInterval(()=>{if(mode&&!document.hidden)tick(mode<0);},1000/12);
draw();
