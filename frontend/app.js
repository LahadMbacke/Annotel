// Default backend base — use same host as the page but default port 8001 (matches the uvicorn you started)
let BACKEND_BASE = `http://${window.location.hostname}:8001`

let docId = null
let textContent = ''
let annotations = []
let selectedLabel = 'PERS'
let lastSelection = null

const textContainer = document.getElementById('text-container')
const docInfo = document.getElementById('doc-info')
const annList = document.getElementById('annotations')
const backendStatusEl = document.getElementById('backend-status')
const backendUrlInput = document.getElementById('backend-url')
const setBackendBtn = document.getElementById('set-backend')
const dirPathInput = document.getElementById('dir-path')
const setDirBtn = document.getElementById('set-dir')
const outDirInput = document.getElementById('out-dir-path')
let backendAvailable = false

// allow changing backend at runtime
if(backendUrlInput){
  backendUrlInput.value = BACKEND_BASE
  if(setBackendBtn){
    setBackendBtn.addEventListener('click', ()=>{
      const v = backendUrlInput.value.trim()
      if(v){ BACKEND_BASE = v; pingBackend() }
    })
  }
}

if(setDirBtn){
  setDirBtn.addEventListener('click', async ()=>{
    const p = (dirPathInput && dirPathInput.value) ? dirPathInput.value.trim() : ''
    const outp = (outDirInput && outDirInput.value) ? outDirInput.value.trim() : ''
    if(!p){ alert('Provide a directory path on the server'); return }
    try{
      const body = outp ? {path: p, output_path: outp} : {path: p}
      const resp = await fetch(`${BACKEND_BASE}/set-directory`, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(body) })
      if(!resp.ok){ alert('Set directory failed: '+await resp.text()); return }
      const j = await resp.json()
      if(j.status === 'ok'){
        docId = j.doc_id
        textContent = j.text
        annotations = j.annotations || []
        updateDocInfo(); renderAnnotatedText(); renderAnnotationsList();
      }else{
        alert(j.message || 'No files found')
      }
    }catch(e){ console.error(e); alert('Error setting directory') }
  })
}

function updateDocInfo(){
  if(!docInfo) return
  docInfo.textContent = `Document: ${docId || '—'} | Annotations: ${annotations.length}`
}

function setBackendStatus(ok, message){
  backendAvailable = ok
  if(!backendStatusEl) return
  backendStatusEl.textContent = ok ? `Backend disponible: ${message || BACKEND_BASE}` : `Backend non disponible: ${message}`
  backendStatusEl.style.color = ok ? 'green' : 'red'
}

function setLabelButtons(){
  document.querySelectorAll('.label-btn').forEach(b => {
    b.addEventListener('click', async ()=>{
      // set active visual
      document.querySelectorAll('.label-btn').forEach(x=>x.classList.remove('active'))
      b.classList.add('active')
      selectedLabel = b.dataset.label

      // Try to get current selection (or lastSelection). If present, save immediately as annotation.
      const sel = getSelectionOffsets()
      if(sel){
        // check overlap
        for(const a of annotations){ if(!(sel.end <= a.start || sel.start >= a.end)){ alert('Sélection chevauche une annotation existante'); return } }
        const ann = { start: sel.start, end: sel.end, label: selectedLabel }
        annotations.push(ann)
        await pushAnnotationsToBackend()
        updateDocInfo()
        renderAnnotatedText()
        renderAnnotationsList()
        try{ window.getSelection().removeAllRanges() }catch(e){}
        lastSelection = null
      }
    })
  })
}

function renderAnnotatedText(){
  if(!textContainer) return
  if(!textContent) { textContainer.textContent = ''; return }
  if(annotations.length === 0){ textContainer.textContent = textContent; return }

  const anns = annotations.slice().sort((a,b)=>a.start-b.start)
  const frag = document.createDocumentFragment()
  let cursor = 0
  for(const ann of anns){
    if(ann.start > cursor){
      frag.appendChild(document.createTextNode(textContent.slice(cursor, ann.start)))
    }
  const span = document.createElement('span')
  span.textContent = textContent.slice(ann.start, ann.end)
  span.className = 'annot'
  span.dataset.label = ann.label
  span.dataset.start = ann.start
  span.dataset.end = ann.end
  // render only the annotated text as a plain text node; the label is shown via CSS ::after using data-label
  span.dataset.label = ann.label
  frag.appendChild(span)
    cursor = ann.end
  }
  if(cursor < textContent.length) frag.appendChild(document.createTextNode(textContent.slice(cursor)))
  textContainer.innerHTML = ''
  textContainer.appendChild(frag)
}

function renderAnnotationsList(){
  if(!annList) return
  annList.innerHTML = ''
  annotations.forEach((a, i) => {
    const li = document.createElement('li')
    li.textContent = `${i}. [${a.label}] (${a.start}-${a.end}): ${textContent.slice(a.start, a.end)}`
    const del = document.createElement('button')
    del.textContent = 'Supprimer'
    del.addEventListener('click', ()=>{ removeAnnotation(i) })
    li.appendChild(del)
    annList.appendChild(li)
  })
}

function removeAnnotation(idx){
  annotations.splice(idx,1)
  pushAnnotationsToBackend()
  updateDocInfo()
  renderAnnotatedText()
  renderAnnotationsList()
}

function getSelectionOffsets(){
  // Try current live selection first
  const sel = window.getSelection()
  if(sel && sel.rangeCount > 0){
    const range = sel.getRangeAt(0)
    if(textContainer.contains(range.startContainer) && textContainer.contains(range.endContainer)){
      const preStart = document.createRange()
      preStart.setStart(textContainer, 0)
      preStart.setEnd(range.startContainer, range.startOffset)
      const start = preStart.toString().length
      const preEnd = document.createRange()
      preEnd.setStart(textContainer, 0)
      preEnd.setEnd(range.endContainer, range.endOffset)
      const end = preEnd.toString().length
      if(end > start) return { start, end, text: textContent.slice(start, end) }
    }
  }

  // Fallback to lastSelection captured on mouseup (useful because clicking a label/button clears the live selection)
  if(lastSelection){
    return lastSelection
  }

  return null
}

async function pushAnnotationsToBackend(){
  if(!docId) return
  try{
    const resp = await fetch(`${BACKEND_BASE}/annotate/${docId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ annotations })
    })
    if(!resp.ok) console.error('Erreur annotate', await resp.text())
  }catch(e){ console.error(e) }
}

const uploadForm = document.getElementById('upload-form')
if(uploadForm){
  uploadForm.addEventListener('submit', async (e)=>{
  e.preventDefault()
  const textArea = document.getElementById('text-input')
  const fileInput = document.getElementById('file-input')
  const fd = new FormData()
  if(fileInput.files.length>0){ fd.append('file', fileInput.files[0]) }
  else fd.append('text', textArea.value)
  try{
    const resp = await fetch(`${BACKEND_BASE}/upload-text`, { method: 'POST', body: fd })
    if(!resp.ok) { alert('Upload failed: '+await resp.text()); return }
    const data = await resp.json()
    docId = data.doc_id
    // fetch text back from backend to ensure normalization
    const tResp = await fetch(`${BACKEND_BASE}/text/${docId}`)
    const j = await tResp.json()
    textContent = j.text
    annotations = j.annotations || []
    updateDocInfo()
    renderAnnotatedText()
    renderAnnotationsList()
  }catch(err){ console.error(err); alert('Upload error') }
  })
}

const saveBtn = document.getElementById('save-selection')
if(saveBtn){
  saveBtn.addEventListener('click', async ()=>{
  const sel = getSelectionOffsets()
  if(!sel){ alert('Sélectionnez d\'abord du texte dans le bloc'); return }
  // basic overlap check
  for(const a of annotations){ if(!(sel.end <= a.start || sel.start >= a.end)){ alert('Sélection chevauche une annotation existante'); return } }
  const ann = { start: sel.start, end: sel.end, label: selectedLabel }
  annotations.push(ann)
  await pushAnnotationsToBackend()
  updateDocInfo()
  renderAnnotatedText()
  renderAnnotationsList()
  // clear live selection and saved lastSelection
  try{ window.getSelection().removeAllRanges() }catch(e){}
  lastSelection = null
  })
}

const exportBtn = document.getElementById('export-btn')
if(exportBtn){
  exportBtn.addEventListener('click', async ()=>{
  if(!docId){ alert('Aucun document à exporter'); return }
  try{
    const resp = await fetch(`${BACKEND_BASE}/export/${docId}`)
    if(!resp.ok){ alert('Export error: '+await resp.text()); return }
    const blob = await resp.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `annotations_${docId}.conll`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
    // after successful export, ask backend for next file (and save .conll on server)
    try{
      const nresp = await fetch(`${BACKEND_BASE}/next`, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({prev_doc_id: docId}) })
      if(!nresp.ok){
        // no more files or server error
        const txt = await nresp.text()
        alert('No next file: '+txt)
        // clear current doc
        docId = null; textContent = ''; annotations = []; updateDocInfo(); renderAnnotatedText(); renderAnnotationsList();
      }else{
        const nj = await nresp.json()
        if(nj.status === 'ok'){
          docId = nj.doc_id
          textContent = nj.text
          annotations = nj.annotations || []
          updateDocInfo(); renderAnnotatedText(); renderAnnotationsList();
        }else{
          alert(nj.message || 'No more files')
          docId = null; textContent = ''; annotations = []; updateDocInfo(); renderAnnotatedText(); renderAnnotationsList();
        }
      }
    }catch(e){ console.error(e) }
  }catch(e){ console.error(e) }
  })
}

// ping backend on load
async function pingBackend(){
  try{
    const resp = await fetch(`${BACKEND_BASE}/list`)
    if(resp.ok){
      setBackendStatus(true, 'OK')
    }else{
      setBackendStatus(false, `HTTP ${resp.status}`)
    }
  }catch(err){
    setBackendStatus(false, err.message)
  }
}

setLabelButtons()
updateDocInfo()
renderAnnotatedText()
renderAnnotationsList()
pingBackend()

// capture selection on mouseup inside the text container so clicking buttons later won't lose it
if(textContainer){
  textContainer.addEventListener('mouseup', ()=>{
  const sel = window.getSelection()
  if(!sel || sel.rangeCount===0) { lastSelection = null; return }
  const range = sel.getRangeAt(0)
  if(!textContainer.contains(range.startContainer) || !textContainer.contains(range.endContainer)) { lastSelection = null; return }
  const preStart = document.createRange()
  preStart.setStart(textContainer, 0)
  preStart.setEnd(range.startContainer, range.startOffset)
  const start = preStart.toString().length
  const preEnd = document.createRange()
  preEnd.setStart(textContainer, 0)
  preEnd.setEnd(range.endContainer, range.endOffset)
  const end = preEnd.toString().length
  if(end > start) lastSelection = { start, end, text: textContent.slice(start, end) }
  else lastSelection = null
  })
}
