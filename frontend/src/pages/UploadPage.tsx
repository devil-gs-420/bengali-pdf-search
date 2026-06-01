import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, FileText, X, CheckCircle2, XCircle, Loader2, FolderOpen } from 'lucide-react'
import { documentsAPI } from '@/utils/api'
import toast from 'react-hot-toast'

interface UploadedFile {
  file: File
  status: 'waiting' | 'uploading' | 'done' | 'error'
  error?: string
}

interface ProgressState {
  sessionId: string
  totalFiles: number
  processedFiles: number
  failedFiles: number
  totalRecords: number
  status: string
  progressPercent: number
}

export default function UploadPage() {
  const [files, setFiles] = useState<UploadedFile[]>([])
  const [folderName, setFolderName] = useState('')
  const [uploading, setUploading] = useState(false)
  const [uploadPct, setUploadPct] = useState(0)
  const [progress, setProgress] = useState<ProgressState | null>(null)
  const [pollInterval, setPollInterval] = useState<ReturnType<typeof setInterval>>()

  const onDrop = useCallback((accepted: File[]) => {
    const pdfs = accepted.filter((f) => f.name.toLowerCase().endsWith('.pdf'))
    if (pdfs.length < accepted.length) {
      toast.error(`${accepted.length - pdfs.length} টি নন-PDF ফাইল বাদ দেওয়া হয়েছে`)
    }
    setFiles((prev) => [
      ...prev,
      ...pdfs.map((f) => ({ file: f, status: 'waiting' as const })),
    ])
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    multiple: true,
  })

  const removeFile = (idx: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== idx))
  }

  const startPolling = (sessionId: string) => {
    const interval = setInterval(async () => {
      try {
        const { data } = await documentsAPI.getProgress(sessionId)
        setProgress({
          sessionId: data.session_id,
          totalFiles: data.total_files,
          processedFiles: data.processed_files,
          failedFiles: data.failed_files,
          totalRecords: data.total_records,
          status: data.status,
          progressPercent: data.progress_percent,
        })
        if (data.status === 'completed' || data.status === 'failed') {
          clearInterval(interval)
          setUploading(false)
          toast.success(`প্রক্রিয়া সম্পন্ন: ${data.total_records} রেকর্ড নিষ্কাশিত`)
        }
      } catch {
        clearInterval(interval)
        setUploading(false)
      }
    }, 2000)
    setPollInterval(interval)
  }

  const handleUpload = async () => {
    if (files.length === 0) return toast.error('কোনো PDF ফাইল নির্বাচন করুন')
    setUploading(true)
    setUploadPct(0)
    setProgress(null)

    try {
      const { data } = await documentsAPI.upload(
        files.map((f) => f.file),
        folderName || 'upload',
        (pct) => setUploadPct(pct)
      )
      setProgress({
        sessionId: data.session_id,
        totalFiles: data.total_files,
        processedFiles: 0,
        failedFiles: 0,
        totalRecords: 0,
        status: 'started',
        progressPercent: 0,
      })
      toast.success(`${data.total_files} টি ফাইল আপলোড সম্পন্ন, প্রক্রিয়া শুরু...`)
      startPolling(data.session_id)
    } catch {
      setUploading(false)
    }
  }

  const resetAll = () => {
    clearInterval(pollInterval)
    setFiles([])
    setProgress(null)
    setUploading(false)
    setUploadPct(0)
    setFolderName('')
  }

  const totalSize = files.reduce((s, f) => s + f.file.size, 0)
  const formatSize = (bytes: number) =>
    bytes > 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.round(bytes / 1024)} KB`

  return (
    <div className="p-6 space-y-6 max-w-3xl mx-auto">
      <div>
        <h1 className="text-xl font-bold text-white">PDF আপলোড</h1>
        <p className="text-sm text-slate-400 mt-0.5">বাংলা ভোটার তালিকা PDF আপলোড করুন</p>
      </div>

      {/* Folder name */}
      <div>
        <label className="block text-sm text-slate-400 mb-1.5">ফোল্ডার / সেশনের নাম (ঐচ্ছিক)</label>
        <div className="relative">
          <FolderOpen className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input
            className="input pl-9"
            placeholder="যেমন: ঢাকা-২০২৪-ভোটার-তালিকা"
            value={folderName}
            onChange={(e) => setFolderName(e.target.value)}
            disabled={uploading}
          />
        </div>
      </div>

      {/* Drop zone */}
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer transition-all duration-200
          ${isDragActive
            ? 'border-sky-500 bg-sky-500/5 dropzone-active'
            : 'border-slate-700 hover:border-slate-500 hover:bg-slate-800/30'
          }
          ${uploading ? 'pointer-events-none opacity-60' : ''}
        `}
      >
        <input {...getInputProps()} />
        <Upload className={`w-10 h-10 mx-auto mb-3 ${isDragActive ? 'text-sky-400' : 'text-slate-500'}`} />
        {isDragActive ? (
          <p className="text-sky-400 font-medium">এখানে ছেড়ে দিন...</p>
        ) : (
          <>
            <p className="text-slate-300 font-medium">PDF ফাইল টেনে এনে ছেড়ে দিন</p>
            <p className="text-slate-500 text-sm mt-1">অথবা ক্লিক করে ফাইল নির্বাচন করুন</p>
            <p className="text-slate-600 text-xs mt-2">সর্বোচ্চ ৫০০MB প্রতি ফাইল · শুধুমাত্র PDF</p>
          </>
        )}
      </div>

      {/* File list */}
      {files.length > 0 && (
        <div className="card overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700/50 bg-slate-800/30">
            <span className="text-sm font-medium text-slate-300">
              {files.length} টি ফাইল · {formatSize(totalSize)}
            </span>
            <button onClick={() => setFiles([])} className="text-xs text-slate-500 hover:text-red-400 transition-colors">
              সব মুছুন
            </button>
          </div>
          <div className="max-h-64 overflow-y-auto">
            {files.map((f, i) => (
              <div key={i} className="flex items-center gap-3 px-4 py-2.5 border-b border-slate-700/30 last:border-0">
                <FileText className="w-4 h-4 text-sky-400 shrink-0" />
                <span className="flex-1 text-sm text-slate-300 truncate">{f.file.name}</span>
                <span className="text-xs text-slate-500 shrink-0">{formatSize(f.file.size)}</span>
                {f.status === 'waiting' && !uploading && (
                  <button onClick={() => removeFile(i)} className="text-slate-600 hover:text-red-400 transition-colors">
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
                {f.status === 'done' && <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />}
                {f.status === 'error' && <XCircle className="w-4 h-4 text-red-400 shrink-0" />}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Upload progress */}
      {(uploading || progress) && (
        <div className="card p-5 space-y-4 animate-slide-up">
          {/* Network upload progress */}
          {uploading && uploadPct < 100 && (
            <div>
              <div className="flex justify-between text-xs text-slate-400 mb-1.5">
                <span>ফাইল আপলোড হচ্ছে...</span>
                <span>{uploadPct}%</span>
              </div>
              <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-sky-500 rounded-full transition-all duration-300"
                  style={{ width: `${uploadPct}%` }}
                />
              </div>
            </div>
          )}

          {/* Processing progress */}
          {progress && (
            <div>
              <div className="flex items-center gap-2 mb-3">
                {progress.status === 'completed' ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                ) : (
                  <Loader2 className="w-4 h-4 text-sky-400 animate-spin" />
                )}
                <span className="text-sm font-medium text-slate-200">
                  {progress.status === 'completed' ? 'প্রক্রিয়া সম্পন্ন' : 'প্রক্রিয়া চলছে...'}
                </span>
              </div>

              <div className="h-2 bg-slate-800 rounded-full overflow-hidden mb-3">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    progress.status === 'completed' ? 'bg-emerald-500' : 'bg-sky-500 progress-animated'
                  }`}
                  style={{ width: `${progress.progressPercent}%` }}
                />
              </div>

              <div className="grid grid-cols-3 gap-4 text-center">
                {[
                  { label: 'প্রক্রিয়াকৃত', value: progress.processedFiles, color: 'text-emerald-400' },
                  { label: 'ব্যর্থ', value: progress.failedFiles, color: 'text-red-400' },
                  { label: 'রেকর্ড', value: progress.totalRecords.toLocaleString(), color: 'text-sky-400' },
                ].map(({ label, value, color }) => (
                  <div key={label} className="bg-slate-800/50 rounded-lg p-3">
                    <p className={`text-lg font-bold ${color}`}>{value}</p>
                    <p className="text-xs text-slate-500 mt-0.5">{label}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Action buttons */}
      <div className="flex gap-3">
        <button
          onClick={handleUpload}
          disabled={files.length === 0 || uploading}
          className="btn-primary flex items-center gap-2 flex-1 justify-center"
        >
          {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
          {uploading ? 'আপলোড হচ্ছে...' : `${files.length} টি PDF আপলোড করুন`}
        </button>
        {(files.length > 0 || progress) && (
          <button onClick={resetAll} className="btn-secondary flex items-center gap-2">
            <X className="w-4 h-4" /> রিসেট
          </button>
        )}
      </div>

      {/* Tips */}
      <div className="card p-4 bg-sky-500/5 border-sky-500/20">
        <p className="text-xs font-medium text-sky-400 mb-2">💡 টিপস</p>
        <ul className="text-xs text-slate-400 space-y-1">
          <li>• টেক্সট PDF ও স্ক্যান করা PDF উভয়ই সমর্থিত</li>
          <li>• স্ক্যান করা PDF-এর জন্য OCR স্বয়ংক্রিয়ভাবে চালু হবে</li>
          <li>• একসাথে অনেক ফাইল আপলোড করা যাবে</li>
          <li>• একই ফাইল দুইবার আপলোড করলে ডুপ্লিকেট সনাক্ত হবে</li>
        </ul>
      </div>
    </div>
  )
}
