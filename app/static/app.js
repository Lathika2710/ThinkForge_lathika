// 1) CSRF token on every POST form
const tok = document.querySelector('meta[name=csrf]').content;
document.querySelectorAll('form[method=post]').forEach(f => {
  if (!f.querySelector('[name=csrf_token]')) {
    const i = document.createElement('input'); i.type = 'hidden'; i.name = 'csrf_token'; i.value = tok; f.appendChild(i);
  }
});

// 2) Auto refresh (worker dashboard / SOS status) unless the user is typing
const ms = parseInt(document.body.dataset.refresh || '0');
if (ms) setInterval(() => {
  const a = document.activeElement;
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
document.querySelectorAll('.mic-btn').forEach(btn => {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  btn.addEventListener('click', () => {
    if (!SR) { alert(document.body.dataset.unsupported); return; }
    const r = new SR(); r.lang = LANGCODE[document.body.dataset.lang] || 'en-IN';
    r.interimResults = false; r.maxAlternatives = 1;
    btn.classList.add('active'); btn.title = document.body.dataset.listening;
    r.onresult = e => {
      const text = e.results[0][0].transcript;
      const box = document.querySelector(btn.dataset.target); box.value = text;
      if (btn.dataset.cat) {
        const sel = document.querySelector(btn.dataset.cat), cat = detect(text);
        if (cat) [...sel.options].forEach(o => { if (o.dataset.name === cat) sel.value = o.value; });
      }
    };
    r.onend = () => btn.classList.remove('active');
    r.onerror = () => btn.classList.remove('active');
    r.start();
  });
});
