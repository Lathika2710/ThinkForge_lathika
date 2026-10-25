// 1) CSRF token on every POST form
const tok = document.querySelector('meta[name=csrf]').content;
document.querySelectorAll('form[method=post]').forEach(f => {
  if (!f.querySelector('[name=csrf_token]')) {
    const i = document.createElement('input'); i.type = 'hidden'; i.name = 'csrf_token'; i.value = tok; f.appendChild(i);
  }
});

// 2) Auto refresh (worker dashboard / SOS status) unless the user is typing or listening to the mic
const ms = parseInt(document.body.dataset.refresh || '0');
let micActive = false;
if (ms) setInterval(() => {
  const a = document.activeElement;
  if (micActive) return;
  if (!a || !['INPUT', 'TEXTAREA', 'SELECT'].includes(a.tagName)) location.reload();
}, ms);

// 3) Voice input (browser speech recognition) -> text + service type from keywords
const LANGCODE = {en: 'en-IN', ta: 'ta-IN', hi: 'hi-IN'};
const KW = {
  'Plumber': ['pipe','leak','tap','water','drain','toilet','tank','பைப்','கசிவு','குழாய்','தண்ணீர்','நீர்','கழிவறை','पाइप','लीक','नल','पानी','टॉयलेट','नाली'],
  'Electrician': ['wire','electric','fan','light','switch','mcb','current','power','shock','spark','மின்','வயர்','விசிறி','பேன்','லைட்','விளக்கு','சுவிட்ச்','ஷாக்','बिजली','तार','पंखा','करंट','लाइट','स्विच','झटका'],
  'Carpenter': ['door','table','chair','wood','furniture','cupboard','window','கதவு','மேசை','நாற்காலி','மரம்','அலமாரி','ஜன்னல்','दरवाज','मेज','कुर्सी','लकड़ी','फर्नीचर','अलमारी','खिड़की'],
  'Painter': ['paint','wall','colour','color','பெயிண்ட்','சுவர்','வண்ணம்','நிறம்','पेंट','दीवार','रंग'],
  'Cleaner': ['clean','dust','wash','sweep','சுத்தம்','கழுவ','தூசி','सफाई','साफ','धुल','झाड़ू'],
  'Cook': ['cook','food','meal','kitchen','சமை','உணவு','சாப்பாடு','खाना','रसोई','कुक','भोजन'],
  'Home Maintenance': ['repair','maintenance','roof','பழுது','பராமரிப்பு','மேற்கூரை','मरम्मत','छत']
};
function detect(text) {
  text = text.toLowerCase(); let best = null, n = 0;
  for (const [cat, words] of Object.entries(KW)) {
    const c = words.filter(w => text.includes(w)).length;
    if (c > n) { n = c; best = cat; }
  }
  return best;
}
function pickCategory(btn, text) {
  if (!btn.dataset.cat) return;
  const sel = document.querySelector(btn.dataset.cat), cat = detect(text);
  if (sel && cat) [...sel.options].forEach(o => { if (o.dataset.name === cat) sel.value = o.value; });
}

const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
const D = document.body.dataset;
let activeRec = null;

document.querySelectorAll('.mic-btn').forEach(btn => {
  const box = document.querySelector(btn.dataset.target);
  if (!box) return;
  // Status line under the input: shows "Listening…", results and clear error messages instead of failing silently.
  const status = document.createElement('div');
  status.className = 'voice-status small mt-1';
  const group = btn.closest('.input-group') || btn.parentElement;
  group.insertAdjacentElement('afterend', status);
  const say = (text, cls) => { status.textContent = text || ''; status.className = 'voice-status small mt-1 ' + (cls || 'text-muted'); };
  const setListening = on => {
    micActive = on;
    btn.classList.toggle('listening', on);
    btn.setAttribute('aria-pressed', on ? 'true' : 'false');
    btn.title = on ? D.listening : '';
  };

  if (!SR) { btn.disabled = true; say(D.unsupported); return; }
  if (!window.isSecureContext) { btn.disabled = true; say(D.voiceInsecure, 'text-danger'); return; }

  btn.addEventListener('click', () => {
    if (activeRec) { activeRec.stop(); return; }          // second tap stops listening
    const r = new SR();
    r.lang = LANGCODE[D.lang] || 'en-IN';
    r.interimResults = true; r.maxAlternatives = 1; r.continuous = false;
    let finalText = '', gotError = false;

    r.onstart = () => { activeRec = r; setListening(true); say(D.listening + ' (' + D.voiceTapStop + ')', 'text-primary'); };
    r.onresult = e => {
      let interim = '';
      for (const res of e.results) { if (res.isFinal) finalText += res[0].transcript + ' '; else interim += res[0].transcript; }
      box.value = (finalText || interim).trim();
    };
    r.onerror = e => {
      gotError = true;
      const code = e.error || '';
      if (code === 'not-allowed' || code === 'service-not-allowed') say(D.voiceDenied, 'text-danger');
      else if (code === 'network') say(D.voiceNetwork, 'text-danger');
      else if (code === 'aborted') say('');
      else if (code === 'language-not-supported' && r.lang !== 'en-IN') {
        // Retry once in English if the chosen UI language has no speech model.
        activeRec = null; setListening(false);
        const r2 = new SR(); Object.assign(r2, {lang: 'en-IN', interimResults: true, maxAlternatives: 1});
        r2.onstart = r.onstart; r2.onresult = r.onresult; r2.onerror = () => say(D.voiceError, 'text-danger'); r2.onend = r.onend;
        try { r2.start(); } catch (err) { say(D.voiceError, 'text-danger'); }
      }
      else say(D.voiceError, 'text-danger');
    };
    r.onend = () => {
      activeRec = null; setListening(false);
      const text = box.value.trim();
      if (text) {
        pickCategory(btn, text);
        box.dispatchEvent(new Event('input', {bubbles: true}));
        if (!gotError) say(D.voiceDone, 'text-success');
        box.focus();
      } else if (!gotError) say(D.voiceError, 'text-danger');
    };
    try { r.start(); } catch (err) { say(D.voiceError, 'text-danger'); }
  });
});
