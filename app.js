'use strict';
const video = document.querySelector('#handoff-video');
const toggle = document.querySelector('#replay-toggle');
let cases = [], replay, phases = [], currentPhase = -1, animationFrame, pendingSeek;
const defaults = {main:'Retain the task goal and returned visual evidence.',subagent:'Choose and inspect the local physical action.',backend:'Plan motion and return fresh observations.'};
const media = file => `assets/media/${file}`;
function setVisual(visual) {
 document.querySelector('#evidence-image').src = media(visual.file);
 document.querySelector('#evidence-image').alt = visual.alt;
 const original = media(visual.original_file || visual.file);
 document.querySelector('#evidence-link').href = original;
 document.querySelector('#original-link').href = original;
}
function renderPhase() {
 if (!phases.length) return;
 const index = phases.reduce((last, phase, i) => video.currentTime >= phase.start_s ? i : last, 0);
 const phase = phases[index];
 if (index !== currentPhase) {
  currentPhase = index;
  document.querySelectorAll('[data-node]').forEach(node => node.classList.toggle('active', node.dataset.node === phase.active_node));
  document.querySelectorAll('[data-phase]').forEach(button => {const active = Number(button.dataset.phase) === index;button.classList.toggle('active',active);button.setAttribute('aria-pressed',String(active));});
  Object.keys(defaults).forEach(node => {document.querySelector(`#${node}-message`).textContent = phase.messages[node] || (node === 'main' ? replay.task : defaults[node]);});
  document.querySelector('#flow-label').textContent = phase.handoff_label;
  const down = document.querySelector('#handoff-down'), back = document.querySelector('#backend-arrow');
  const direct = phase.flow.includes('main') && phase.flow.includes('backend');
  down.classList.toggle('active',!direct && phase.flow.includes('main'));back.classList.toggle('active',!direct && phase.flow.includes('backend'));
  down.firstElementChild.textContent = phase.flow[1] === 'main' ? '←' : '→';back.firstElementChild.textContent = phase.flow[0] === 'backend' ? '←' : '→';
  document.querySelector('#phase-counter').textContent = `${String(index+1).padStart(2,'0')} / ${phases.length}`;
  document.querySelector('#phase-name').textContent = phase.title;
  const evidence = phase.visual;
  setVisual(evidence);
  document.querySelector('#evidence-label').textContent = evidence.label;
  document.querySelector('#evidence-kind').textContent = evidence.kind;
  document.querySelector('#evidence-caption').textContent = phase.detail;
  document.querySelector('#evidence-detail').textContent = evidence.note;
  const gallery = document.querySelector('#candidate-nav');gallery.replaceChildren();
  (phase.candidates || []).forEach(candidate => {
   const button = document.createElement('button');button.type = 'button';
   const image = document.createElement('img');image.src=media(candidate.file);image.alt='';
   const label = document.createElement('span');label.textContent=candidate.label;
   button.append(image,label);button.classList.toggle('recorded-selection',Boolean(candidate.selected));
   button.setAttribute('aria-label',`Inspect ${candidate.label}`);
   button.addEventListener('click',()=>{setVisual({...candidate,alt:candidate.label});});gallery.append(button);
  });
 }
 document.querySelector('#replay-time').textContent = `${video.currentTime.toFixed(1)} s`;
 const camera = replay.camera_frames;
 if (camera) {
  const sequence=phase.camera_sequence || [];
  const progress=(video.currentTime-phase.start_s)/(phase.end_s-phase.start_s);
  const observation=sequence[Math.min(Math.floor(Math.max(0,progress)*sequence.length),sequence.length-1)];
  document.querySelector('#capture-label').textContent = observation ? `Camera capture ${observation.capture_id} · +${observation.offset_s.toFixed(1)} s in the recorded run` : '';
 } else document.querySelector('#capture-label').textContent='Original arm motion with pauses for reading.';
}
function renderPlayback() {toggle.textContent=video.paused?(video.ended?'Replay demo':'Play demo'):'Pause demo';toggle.setAttribute('aria-pressed',String(!video.paused));}
function animate() {renderPhase();if(!video.paused)animationFrame=requestAnimationFrame(animate);}
function jump(index) {video.pause();video.currentTime=phases[index].start_s;currentPhase=-1;renderPhase();}
function chooseCase(id,step='Point') {
 video.pause();replay=cases.find(item=>item.id===id)||cases[0];phases=replay.phases;currentPhase=-1;
 video.src=media(replay.video_file);video.poster=media(replay.poster_file);video.load();
 document.querySelector('#case-goal').textContent=replay.task;
 document.querySelector('#motion-label').textContent=replay.motion_label;
 document.querySelector('#timing-note').textContent=replay.timing_note;
 document.querySelector('#demo-download').href=media(replay.demo_file);
 document.querySelectorAll('[data-execution]').forEach(button=>{const active=button.dataset.execution===replay.id;button.classList.toggle('active',active);button.setAttribute('aria-pressed',String(active));});
 const nav=document.querySelector('#phase-nav');nav.replaceChildren();
 phases.forEach((phase,index)=>{const button=document.createElement('button');button.type='button';button.dataset.phase=index;button.textContent=phase.short;button.addEventListener('click',()=>jump(index));nav.append(button);});
 const index=Math.max(0,phases.findIndex(phase=>phase.short===step));
 if(pendingSeek)video.removeEventListener('loadedmetadata',pendingSeek);
 pendingSeek=()=>{jump(index);pendingSeek=null;};
 video.addEventListener('loadedmetadata',pendingSeek,{once:true});renderPhase();renderPlayback();
}
async function startReplay() {
 try {
  const response=await fetch('data/handoff.json');if(!response.ok)throw new Error('Trace unavailable');
  cases=(await response.json()).cases;
  const nav=document.querySelector('#case-nav');
  cases.forEach(item=>{const button=document.createElement('button');button.type='button';button.dataset.execution=item.id;button.textContent=item.label;button.addEventListener('click',()=>chooseCase(item.id));nav.append(button);});
  document.querySelectorAll('[data-case]').forEach(button=>button.addEventListener('click',()=>{chooseCase(button.dataset.case,button.dataset.step);document.querySelector('.replay').scrollIntoView({behavior:'smooth',block:'start'});}));
  chooseCase(cases[0].id);
 } catch {toggle.disabled=true;document.querySelector('#evidence-detail').textContent='Visual trace could not load. Please reload the page.';}
}
toggle.addEventListener('click',async()=>{if(video.paused){if(video.ended)video.currentTime=0;try{await video.play();}catch{toggle.textContent='Use video controls';}}else video.pause();});
video.addEventListener('play',()=>{renderPlayback();cancelAnimationFrame(animationFrame);animate();});
video.addEventListener('pause',()=>{renderPlayback();cancelAnimationFrame(animationFrame);});
video.addEventListener('ended',()=>{renderPlayback();renderPhase();});
video.addEventListener('seeked',renderPhase);video.addEventListener('timeupdate',renderPhase);
document.querySelectorAll('[data-pair]').forEach(pair => {
 const videos = [...pair.querySelectorAll('video')];
 pair.querySelector('button').addEventListener('click', async () => {
  videos.forEach(v => {v.pause();v.currentTime = 0;});await Promise.allSettled(videos.map(v => v.play()));
 });
});
document.querySelectorAll('[data-copy]').forEach(button => button.addEventListener('click', async () => {
 const code = document.getElementById(button.dataset.copy);
 try {await navigator.clipboard.writeText(code.textContent);button.textContent = 'Copied';}
 catch {const range = document.createRange();range.selectNodeContents(code);const selection = window.getSelection();selection.removeAllRanges();selection.addRange(range);button.textContent = 'Select & copy';}
}));
const links = [...document.querySelectorAll('.rail a')];
const observer = new IntersectionObserver(entries => {
 const visible = entries.filter(e => e.isIntersecting).sort((a,b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
 if (visible) links.forEach(link => {if (link.hash === `#${visible.target.id}`) link.setAttribute('aria-current','location');else link.removeAttribute('aria-current');});
}, {rootMargin:'-5% 0px -65% 0px'});
document.querySelectorAll('.section h2').forEach(heading => observer.observe(heading));
document.addEventListener('visibilitychange', () => {if (document.hidden) document.querySelectorAll('video').forEach(v => v.pause());});
startReplay();
