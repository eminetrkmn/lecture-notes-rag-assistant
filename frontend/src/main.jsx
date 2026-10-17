import React, { useEffect, useRef, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { BookOpen, UploadCloud, FileText, Trash2, Send, Sparkles, BrainCircuit, Library, ChevronRight, CheckCircle2, XCircle, Loader2, RotateCcw, ShieldCheck, PanelLeftClose, Menu, GraduationCap, ExternalLink } from 'lucide-react'
import './style.css'

const API = '/api'
async function request(url, init) {
  const res = await fetch(API + url, init)
  if (!res.ok) {
    let payload = {}
    try { payload = await res.json() } catch {}
    throw new Error(typeof payload.detail === 'string' ? payload.detail : `HTTP ${res.status}`)
  }
  return res.status === 204 ? null : res.json()
}

function App() {
  const [docs, setDocs] = useState([])
  const [selected, setSelected] = useState([])
  const [view, setView] = useState('chat')
  const [message, setMessage] = useState('')
  const [history, setHistory] = useState([])
  const [busy, setBusy] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const [quiz, setQuiz] = useState([])
  const [choices, setChoices] = useState({})
  const [reveal, setReveal] = useState(false)
  const [mobileMenu, setMobileMenu] = useState(false)
  const [drag, setDrag] = useState(false)
  const inputRef = useRef(null)
  const endRef = useRef(null)

  const refresh = async () => {
    try {
      const list = await request('/documents')
      setDocs(list)
      setSelected(prev => prev.filter(id => list.some(d => d.id === id)))
    } catch (e) { setError(e.message) }
  }
  useEffect(() => { refresh() }, [])
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [history, busy])

  async function upload(file) {
    if (!file) return
    if (!file.name.toLowerCase().endsWith('.pdf')) return setError('Lütfen bir PDF dosyası seç.')
    setError(''); setUploading(true)
    const form = new FormData(); form.append('file', file)
    try {
      const doc = await request('/documents', { method: 'POST', body: form })
      await refresh()
      setSelected(prev => [...prev, doc.id])
      setView('chat'); setHistory([]); setQuiz([])
    } catch (e) { setError(e.message) }
    finally { setUploading(false); if (inputRef.current) inputRef.current.value = '' }
  }

  async function remove(id) {
    if (!window.confirm('Bu belgeyi ve indeksini silmek istiyor musun?')) return
    setError('')
    try { await request('/documents/' + encodeURIComponent(id), { method: 'DELETE' }); await refresh(); setHistory([]); setQuiz([]) }
    catch (e) { setError(e.message) }
  }

  async function ask(e) {
    e?.preventDefault()
    const text = message.trim()
    if (!text || busy || !selected.length) return
    setMessage(''); setError(''); setBusy(true)
    setHistory(prev => [...prev, { role: 'user', text }])
    try {
      const data = await request('/ask', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: text, document_ids: selected }) })
      setHistory(prev => [...prev, { role: 'assistant', text: data.answer, sources: data.sources }])
    } catch (e) { setError(e.message) }
    finally { setBusy(false) }
  }

  async function makeQuiz() {
    if (!selected.length || busy) return
    setBusy(true); setError(''); setQuiz([]); setChoices({}); setReveal(false)
    try {
      const data = await request('/quiz', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ document_ids: selected, count: 5 }) })
      setQuiz(data.questions)
    } catch (e) { setError(e.message) }
    finally { setBusy(false) }
  }
  const score = quiz.reduce((sum, q, i) => sum + (choices[i] === q.correct_index ? 1 : 0), 0)
  const switchView = (v) => { setView(v); setMobileMenu(false); setError('') }

  return <div className="app">
    <aside className={'sidebar ' + (mobileMenu ? 'open' : '')}>
      <div className="brand"><div className="brand-icon"><BookOpen size={23}/></div><div><b>notely<span>.</span></b><small>YOUR AI STUDY SPACE</small></div></div>
      <div className="nav-title">WORKSPACE</div>
      <button className={'nav ' + (view === 'chat' ? 'active' : '')} onClick={() => switchView('chat')}><Sparkles size={18}/> AI ile Sohbet <ChevronRight size={15} className="nav-chevron"/></button>
      <button className={'nav ' + (view === 'quiz' ? 'active' : '')} onClick={() => switchView('quiz')}><BrainCircuit size={18}/> Quiz Oluştur <ChevronRight size={15} className="nav-chevron"/></button>
      <div className="doc-heading"><span>DERS NOTLARIM</span><span className="count">{docs.length}</span></div>
      <div className="docs">{docs.length === 0 && <p className="empty-docs">Henüz PDF yüklenmedi.</p>}
        {docs.map(d => <div className="doc" key={d.id}>
          <label className="doc-select"><input type="checkbox" checked={selected.includes(d.id)} onChange={() => { setSelected(prev => prev.includes(d.id) ? prev.filter(x => x !== d.id) : [...prev, d.id]); setHistory([]); setQuiz([]) }}/><FileText size={16}/><span title={d.filename}>{d.filename}<small>{d.pages} sayfa · {d.chunks} parça</small></span></label>
          <button className="delete" title="Belgeyi sil" aria-label="Belgeyi sil" onClick={() => remove(d.id)}><Trash2 size={15}/></button>
        </div>)}
      </div>
      <div className={'upload-area ' + (drag ? 'drag' : '')} onDragOver={e => {e.preventDefault(); setDrag(true)}} onDragLeave={() => setDrag(false)} onDrop={e => {e.preventDefault(); setDrag(false); upload(e.dataTransfer.files[0])}} onClick={() => !uploading && inputRef.current?.click()}>
        {uploading ? <Loader2 size={24} className="spin"/> : <UploadCloud size={25}/>}<strong>{uploading ? 'PDF işleniyor...' : 'PDF Yükle'}</strong><span>Dosyanı sürükle veya seç</span><small>Maksimum 20 MB</small><input ref={inputRef} type="file" accept=".pdf,application/pdf" hidden onChange={e => upload(e.target.files[0])}/>
      </div>
      <div className="sidebar-foot"><ShieldCheck size={16}/> Kaynak odaklı yapay zekâ</div>
    </aside>
    {mobileMenu && <div className="overlay" onClick={() => setMobileMenu(false)}/>}
    <main className="main">
      <header className="topbar"><button className="menu-btn" onClick={() => setMobileMenu(true)}><Menu size={21}/></button><div className="crumb"><span>Workspace</span><ChevronRight size={14}/><strong>{view === 'chat' ? 'AI Sohbet' : 'Quiz Studio'}</strong></div><div className="top-pill"><span className="dot"/> RAG POWERED</div></header>
      {error && <div className="error" role="alert">{error}<button onClick={() => setError('')}>×</button></div>}
      {view === 'chat' ? <section className="chat-content">
        {history.length === 0 ? <div className="welcome"><div className="hero-icon"><GraduationCap size={32}/></div><div className="eyebrow">AKILLI ÇALIŞMA ASİSTANIN</div><h1>Notlarına sor,<br/><em>bilgiye ulaş.</em></h1><p>PDF ders notlarını yükle, merak ettiğin soruları sor. Yanıtlarını doğrudan notlarından, sayfa referanslarıyla al.</p><div className="suggestions">{['Bu konuyu kısaca özetle', 'En önemli kavramlar neler?', 'Sınav için neye çalışmalıyım?'].map(s => <button key={s} disabled={!selected.length} onClick={() => setMessage(s)}><Sparkles size={14}/>{s}<ChevronRight size={14}/></button>)}</div></div>
          : <div className="messages">{history.map((h, i) => <div key={i} className={'msg ' + h.role}><div className="msg-avatar">{h.role === 'user' ? 'S' : <Sparkles size={17}/>}</div><div className="msg-body"><strong>{h.role === 'user' ? 'Sen' : 'Notely AI'}</strong><p>{h.text}</p>{h.sources?.length > 0 && <div className="sources"><div className="source-label"><Library size={14}/> KULLANILAN KAYNAKLAR</div>{h.sources.map((s, j) => <details key={j}><summary><span className="source-num">{j+1}</span><FileText size={14}/><span className="source-name">{s.filename}</span><span className="page">Sayfa {s.page}</span><ChevronRight size={14}/></summary><p>{s.excerpt}</p></details>)}</div>}</div></div>)}{busy && <div className="msg assistant"><div className="msg-avatar"><Sparkles size={17}/></div><div className="typing"><span/><span/><span/></div></div>}<div ref={endRef}/></div>}
        <div className="composer-wrap"><form className="composer" onSubmit={ask}><input value={message} onChange={e => setMessage(e.target.value)} disabled={!selected.length || busy} placeholder={selected.length ? 'Notların hakkında bir soru sor...' : 'Başlamak için sol menüden PDF yükle ve seç'} aria-label="Sorun"/><button disabled={!message.trim() || !selected.length || busy} aria-label="Gönder"><Send size={19}/></button></form><div className="composer-note"><ShieldCheck size={13}/> Yanıtlar yüklediğin dokümanlardan oluşturulur. Önemli bilgileri kaynaklardan doğrula.</div></div>
      </section> : <section className="quiz-view"><div className="quiz-head"><div className="quiz-icon"><BrainCircuit size={27}/></div><span className="eyebrow">AKTİF ÖĞRENME</span><h1>Bilgini <em>test et.</em></h1><p>Seçtiğin notlarından yapay zekâ ile oluşturulmuş 5 soruluk mini sınav.</p><button className="primary" disabled={!selected.length || busy} onClick={makeQuiz}>{busy ? <Loader2 className="spin" size={18}/> : <Sparkles size={18}/>} {busy ? 'Sorular hazırlanıyor...' : quiz.length ? 'Yeni Quiz Oluştur' : 'Quiz Oluştur'}</button>{!selected.length && <div className="quiz-hint">Önce bir PDF yükleyip seçmelisin.</div>}</div>
        {quiz.length > 0 && <div className="quiz-questions">{quiz.map((q, i) => <article className="question" key={i}><div className="question-top"><span>SORU {String(i+1).padStart(2,'0')}</span>{q.source_page && <span>Sayfa {q.source_page}</span>}</div><h3>{q.question}</h3><div className="options">{q.options.map((o, j) => <button key={j} disabled={reveal} onClick={() => setChoices(prev => ({...prev, [i]: j}))} className={'option ' + (choices[i] === j ? 'chosen ' : '') + (reveal && j === q.correct_index ? 'correct ' : '') + (reveal && choices[i] === j && j !== q.correct_index ? 'wrong' : '')}><span className="letter">{'ABCD'[j]}</span><span>{o}</span>{reveal && j === q.correct_index && <CheckCircle2 size={18}/>} {reveal && choices[i] === j && j !== q.correct_index && <XCircle size={18}/>}</button>)}</div>{reveal && <div className="explanation"><strong>Açıklama</strong><p>{q.explanation}</p></div>}</article>)}<div className="quiz-result">{reveal ? <><strong>Sonuç: {score} / {quiz.length}</strong><button className="primary" onClick={makeQuiz}><RotateCcw size={17}/> Tekrar Dene</button></> : <button className="primary" disabled={Object.keys(choices).length !== quiz.length} onClick={() => setReveal(true)}>Sonuçları Gör <ChevronRight size={17}/></button>}</div></div>}
      </section>}
    </main>
  </div>
}

createRoot(document.getElementById('root')).render(<App />)
