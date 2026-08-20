import { useEffect, useState } from 'react'
import * as api from '../api.js'
import { buildMarkdown } from '../utils.js'

// Obsidian vault 連線狀態、資料夾/筆記清單、存檔選項與存檔動作
export default function useNotesVault(initialSaveOpts, videoTitle = '') {
  const [vault, setVault] = useState({ configured: false, exists: false, path: null })
  const [baseFolder, setBaseFolder] = useState('')
  const [folders, setFolders] = useState([])
  const [noteFiles, setNoteFiles] = useState([])
  const [saveOpts, setSaveOpts] = useState(initialSaveOpts || { folder: '', mode: 'new', targetFile: '' })
  const [saving, setSaving] = useState(false)

  function computeVideoFolder(base, title) {
    const clean = sanitizeFolderName(title)
    if (!clean) return base || ''
    return base ? `${base}/${clean}` : clean
  }

  function refresh(overrideTitle) {
    const activeTitle = overrideTitle !== undefined ? overrideTitle : videoTitle
    api.notesStatus().then(v => {
      setVault(v)
      if (v.configured) api.notesFolders().then(r => {
        const def = r.default || v.default_folder || ''
        setBaseFolder(def)
        const videoSub = computeVideoFolder(def, activeTitle)
        const allFolders = Array.from(new Set([videoSub, def, ...(r.folders || [])].filter(f => f !== null && f !== undefined)))
        setFolders(allFolders)
        setSaveOpts(s => ({
          ...s,
          folder: s.folder !== undefined && s.folder !== null && s.folder !== '' ? s.folder : videoSub
        }))
      })
    })
  }

  useEffect(() => { refresh() }, [])

  // 當影片標題產生時，自動將儲存資料夾更新為該影片的專屬子資料夾
  useEffect(() => {
    if (videoTitle) {
      const videoSub = computeVideoFolder(baseFolder, videoTitle)
      if (videoSub) {
        setFolders(prev => Array.from(new Set([videoSub, ...prev])))
        setSaveOpts(s => ({ ...s, folder: videoSub }))
      }
    }
  }, [videoTitle, baseFolder])

  // 切到「附加到現有筆記」或更換資料夾時，載入該資料夾的筆記清單
  useEffect(() => {
    if (saveOpts.mode === 'append' && vault.configured) api.notesFiles(saveOpts.folder).then(r => setNoteFiles(r.files || []))
  }, [saveOpts.folder, saveOpts.mode, vault.configured])

  const onSaveOptsChange = patch => setSaveOpts(prev => {
    const next = { ...prev, ...patch }
    if ('folder' in patch) next.targetFile = ''
    return next
  })

  // t 由呼叫端傳入：筆記內容的區塊標題要跟著介面語言走
  async function save({ title, sourceUrl, clips, freeNote, t }) {
    if (saving) return null
    if (saveOpts.mode === 'append' && !saveOpts.targetFile) throw new Error(t('error.pickNote'))
    const md = buildMarkdown({ title, sourceUrl, clips, freeNote, mode: saveOpts.mode, t })
    setSaving(true)
    try {
      const res = await api.saveNote({ filename: title, content: md, folder: saveOpts.folder, mode: saveOpts.mode, target_file: saveOpts.targetFile })
      if (saveOpts.mode === 'append') api.notesFiles(saveOpts.folder).then(r => setNoteFiles(r.files || []))
      return res
    } finally {
      setSaving(false)
    }
  }

  return { vault, baseFolder, folders, noteFiles, saveOpts, onSaveOptsChange, saving, save, refresh }
}
