import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  FileText, RefreshCw, Trash2, CheckCircle2, XCircle,
  Clock, Loader2, ChevronLeft, ChevronRight, Filter
} from 'lucide-react'
import { documentsAPI } from '@/utils/api'
import { Document, DocumentListResponse } from '@/types'
import { useAuthStore } from '@/store/authStore'
import toast from 'react-hot-toast'

const STATUS_OPTIONS = [
  { value: '', label: 'সব' },
  { value: 'completed', label: 'সম্পন্ন' },
  { value: 'processing', label: 'প্রক্রিয়াধীন' },
  { value: 'pending', label: 'অপেক্ষমান' },
  { value: 'failed', label: 'ব্যর্থ' },
]

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { cls: string; icon: React.ReactNode; label: string }> = {
    completed:  { cls: 'badge-success', icon: <CheckCircle2 className="w-3 h-3" />, label: 'সম্পন্ন' },
    failed:     { cls: 'badge-error',   icon: <XCircle className="w-3 h-3" />,      label: 'ব্যর্থ' },
    processing: { cls: 'badge-warning', icon: <Loader2 className="w-3 h-3 animate-spin" />, label: 'প্রক্রিয়াধীন' },
    pending:    { cls: 'badge-muted',   icon: <Clock className="w-3 h-3" />,         label: 'অপেক্ষমান' },
  }
  const s = map[status] || map.pending
  return (
    <span className={`${s.cls} flex items-center gap-1`}>
      {s.icon}{s.label}
    </span>
  )
}

function formatBytes(bytes?: number) {
  if (!bytes) return '—'
  if (bytes > 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  return `${Math.round(bytes / 1024)} KB`
}

export default function DocumentsPage() {
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState('')
  const user = useAuthStore((s) => s.user)
  const qc = useQueryClient()
  const PAGE_SIZE = 20

  const { data, isLoading } = useQuery<DocumentListResponse>({
    queryKey: ['documents', page, statusFilter],
    queryFn: () =>
      documentsAPI.list(page, PAGE_SIZE, statusFilter || undefined).then((r) => r.data),
    refetchInterval: 15_000,
  })

  const reprocessMutation = useMutation({
    mutationFn: (id: number) => documentsAPI.reprocess(id),
    onSuccess: () => {
      toast.success('পুনরায় প্রক্রিয়া শুরু হয়েছে')
      qc.invalidateQueries({ queryKey: ['documents'] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => documentsAPI.delete(id),
    onSuccess: () => {
      toast.success('ডকুমেন্ট মুছে ফেলা হয়েছে')
      qc.invalidateQueries({ queryKey: ['documents'] })
    },
  })

  const handleDelete = (doc: Document) => {
    if (window.confirm(`"${doc.filename}" মুছে ফেলতে চান?`)) {
      deleteMutation.mutate(doc.id)
    }
  }

  const totalPages = data?.pages || 1

  return (
    <div className="p-6 space-y-5 max-w-7xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">ডকুমেন্ট তালিকা</h1>
          {data && <p className="text-sm text-slate-400 mt-0.5">মোট {data.total.toLocaleString()} টি ডকুমেন্ট</p>}
        </div>

        {/* Status filter */}
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-slate-500" />
          <div className="flex gap-1">
            {STATUS_OPTIONS.map(({ value, label }) => (
              <button
                key={value}
                onClick={() => { setStatusFilter(value); setPage(1) }}
                className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                  statusFilter === value
                    ? 'bg-sky-500/20 text-sky-400 border border-sky-500/30'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-14 skeleton rounded-lg" />
          ))}
        </div>
      ) : !data?.items.length ? (
        <div className="card p-12 text-center">
          <FileText className="w-10 h-10 text-slate-600 mx-auto mb-3" />
          <p className="text-slate-400">কোনো ডকুমেন্ট পাওয়া যায়নি</p>
        </div>
      ) : (
        <>
          <div className="table-container">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-700 bg-slate-800/50">
                  {['#', 'ফাইলের নাম', 'স্ট্যাটাস', 'পৃষ্ঠা', 'রেকর্ড', 'আকার', 'সময়', 'তারিখ', ''].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-medium text-slate-400 whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.items.map((doc) => (
                  <tr key={doc.id} className="table-row">
                    <td className="px-4 py-3 text-slate-500 font-mono text-xs">{doc.id}</td>
                    <td className="px-4 py-3 max-w-[200px]">
                      <div className="flex items-center gap-2">
                        <FileText className="w-3.5 h-3.5 text-sky-400 shrink-0" />
                        <span className="text-slate-200 truncate text-xs">{doc.filename}</span>
                        {doc.is_scanned && (
                          <span className="badge badge-info text-xs shrink-0">OCR</span>
                        )}
                      </div>
                      {doc.error_message && (
                        <p className="text-xs text-red-400 mt-0.5 truncate">{doc.error_message}</p>
                      )}
                    </td>
                    <td className="px-4 py-3"><StatusBadge status={doc.status} /></td>
                    <td className="px-4 py-3 text-slate-400 text-xs">{doc.page_count ?? '—'}</td>
                    <td className="px-4 py-3">
                      <span className="text-emerald-400 font-medium">{doc.records_extracted.toLocaleString()}</span>
                    </td>
                    <td className="px-4 py-3 text-slate-500 text-xs whitespace-nowrap">{formatBytes(doc.file_size)}</td>
                    <td className="px-4 py-3 text-slate-500 text-xs whitespace-nowrap">
                      {doc.processing_time_seconds ? `${doc.processing_time_seconds.toFixed(1)}s` : '—'}
                    </td>
                    <td className="px-4 py-3 text-slate-500 text-xs whitespace-nowrap">
                      {new Date(doc.created_at).toLocaleDateString('bn-BD')}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1">
                        {doc.status === 'failed' && (
                          <button
                            onClick={() => reprocessMutation.mutate(doc.id)}
                            disabled={reprocessMutation.isPending}
                            title="পুনরায় প্রক্রিয়া করুন"
                            className="p-1.5 rounded text-slate-500 hover:text-amber-400 hover:bg-amber-400/10 transition-colors"
                          >
                            <RefreshCw className="w-3.5 h-3.5" />
                          </button>
                        )}
                        {user?.role === 'admin' && (
                          <button
                            onClick={() => handleDelete(doc)}
                            disabled={deleteMutation.isPending}
                            title="মুছুন"
                            className="p-1.5 rounded text-slate-500 hover:text-red-400 hover:bg-red-400/10 transition-colors"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between text-sm">
            <p className="text-slate-400">
              {((page - 1) * PAGE_SIZE) + 1}–{Math.min(page * PAGE_SIZE, data.total)} / {data.total.toLocaleString()}
            </p>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="btn-secondary px-2 py-1.5 disabled:opacity-40"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="px-3 text-slate-400">{page} / {totalPages}</span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="btn-secondary px-2 py-1.5 disabled:opacity-40"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
