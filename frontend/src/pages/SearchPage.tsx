import { useState, useCallback, useRef } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { Search, Filter, Download, ChevronLeft, ChevronRight, X, SlidersHorizontal, Loader2 } from 'lucide-react'
import { searchAPI, exportAPI } from '@/utils/api'
import { VoterRecord, VoterRecordListResponse, SearchFilters } from '@/types'
import toast from 'react-hot-toast'

const PAGE_SIZE = 20

function RecordDetail({ record, onClose }: { record: VoterRecord; onClose: () => void }) {
  const fields: [string, string | undefined | number][] = [
    ['ভোটার নম্বর', record.voter_id],
    ['ক্রমিক নম্বর', record.serial_number],
    ['নাম', record.name],
    ['পিতার নাম', record.father_name],
    ['মাতার নাম', record.mother_name],
    ['স্বামী/স্ত্রী', record.spouse_name],
    ['জন্মতারিখ', record.birth_date],
    ['লিঙ্গ', record.gender],
    ['পেশা', record.occupation],
    ['ঠিকানা', record.address],
    ['গ্রাম', record.village],
    ['ডাকঘর', record.post_office],
    ['ইউনিয়ন', record.union_name],
    ['ওয়ার্ড', record.ward],
    ['উপজেলা', record.upazila],
    ['জেলা', record.district],
    ['বিভাগ', record.division],
    ['PDF ফাইল', record.pdf_file_name],
    ['পৃষ্ঠা নম্বর', record.page_number],
  ]

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-lg max-h-[80vh] overflow-y-auto shadow-2xl">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700">
          <h3 className="font-semibold text-white bengali">{record.name || 'ভোটার বিবরণ'}</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-5">
          <div className="grid grid-cols-2 gap-x-4 gap-y-3">
            {fields.filter(([, v]) => v).map(([label, value]) => (
              <div key={label}>
                <p className="text-xs text-slate-500">{label}</p>
                <p className="text-sm text-slate-200 mt-0.5 bengali break-words">{String(value)}</p>
              </div>
            ))}
          </div>
          {record.extraction_confidence != null && (
            <div className="mt-4 pt-4 border-t border-slate-700">
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-500">নিষ্কাশন নির্ভরযোগ্যতা</span>
                <span className="text-slate-400">{Math.round(record.extraction_confidence * 100)}%</span>
              </div>
              <div className="h-1 bg-slate-700 rounded-full mt-1 overflow-hidden">
                <div
                  className="h-full bg-sky-500 rounded-full"
                  style={{ width: `${Math.round(record.extraction_confidence * 100)}%` }}
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default function SearchPage() {
  const [filters, setFilters] = useState<SearchFilters>({ page: 1, page_size: PAGE_SIZE })
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [selectedRecord, setSelectedRecord] = useState<VoterRecord | null>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout>>()
  const [liveQuery, setLiveQuery] = useState('')

  // Debounced search trigger
  const triggerSearch = useCallback((newFilters: SearchFilters) => {
    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      setFilters({ ...newFilters, page: 1 })
    }, 350)
  }, [])

  const { data, isFetching } = useQuery<VoterRecordListResponse>({
    queryKey: ['search', filters],
    queryFn: () => {
      const params: Record<string, string | number> = {}
      Object.entries(filters).forEach(([k, v]) => {
        if (v !== undefined && v !== '') params[k] = v
      })
      return searchAPI.search(params).then((r) => r.data)
    },
    enabled: Object.keys(filters).some(k => !['page', 'page_size'].includes(k) && filters[k as keyof SearchFilters]),
    placeholderData: (prev) => prev,
  })

  const exportMutation = useMutation({
    mutationFn: (format: string) =>
      exportAPI.export({ format, query: filters.query, filters, max_records: 10000 }),
    onSuccess: (res, format) => {
      const blob = new Blob([res.data])
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `voter_records.${format === 'excel' ? 'xlsx' : format}`
      a.click()
      URL.revokeObjectURL(url)
      toast.success('এক্সপোর্ট সম্পন্ন')
    },
  })

  const setFilter = (key: keyof SearchFilters, value: string) => {
    const updated = { ...filters, [key]: value || undefined }
    setFilters(updated)
    triggerSearch(updated)
  }

  const clearFilters = () => {
    setLiveQuery('')
    setFilters({ page: 1, page_size: PAGE_SIZE })
  }

  const hasResults = data && data.total > 0
  const totalPages = data?.pages || 1

  return (
    <div className="p-6 space-y-4 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">ভোটার অনুসন্ধান</h1>
          {data && (
            <p className="text-sm text-slate-400 mt-0.5">
              {data.total.toLocaleString()} টি ফলাফল
              {data.search_duration_ms && ` · ${data.search_duration_ms}ms`}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowAdvanced(!showAdvanced)}
            className={`btn-secondary text-sm flex items-center gap-2 ${showAdvanced ? 'ring-1 ring-sky-500/50' : ''}`}
          >
            <SlidersHorizontal className="w-4 h-4" />
            ফিল্টার
          </button>
          <div className="relative">
            <button className="btn-secondary text-sm flex items-center gap-2 group">
              <Download className="w-4 h-4" />
              এক্সপোর্ট
            </button>
            {/* Export dropdown - shown on hover via group */}
          </div>
        </div>
      </div>

      {/* Main search bar */}
      <div className="relative">
        <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
        <input
          type="text"
          className="input pl-10 pr-10 text-base"
          placeholder="নাম, পিতার নাম, ভোটার নম্বর, ঠিকানা দিয়ে খুঁজুন..."
          value={liveQuery}
          onChange={(e) => {
            setLiveQuery(e.target.value)
            triggerSearch({ ...filters, query: e.target.value || undefined })
          }}
        />
        {(liveQuery || isFetching) && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2">
            {isFetching
              ? <Loader2 className="w-4 h-4 text-sky-400 animate-spin" />
              : <button onClick={clearFilters}><X className="w-4 h-4 text-slate-500 hover:text-white" /></button>
            }
          </div>
        )}
      </div>

      {/* Advanced filters */}
      {showAdvanced && (
        <div className="card p-4 animate-slide-up">
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            {[
              { key: 'name', label: 'নাম', ph: 'ভোটারের নাম' },
              { key: 'father_name', label: 'পিতার নাম', ph: 'পিতার নাম' },
              { key: 'mother_name', label: 'মাতার নাম', ph: 'মাতার নাম' },
              { key: 'voter_id', label: 'ভোটার নম্বর', ph: 'ভোটার নম্বর' },
              { key: 'district', label: 'জেলা', ph: 'জেলার নাম' },
              { key: 'upazila', label: 'উপজেলা', ph: 'উপজেলার নাম' },
              { key: 'union_name', label: 'ইউনিয়ন', ph: 'ইউনিয়নের নাম' },
              { key: 'ward', label: 'ওয়ার্ড', ph: 'ওয়ার্ড নম্বর' },
              { key: 'village', label: 'গ্রাম', ph: 'গ্রামের নাম' },
              { key: 'occupation', label: 'পেশা', ph: 'পেশা' },
              { key: 'birth_date', label: 'জন্মতারিখ', ph: 'জন্মতারিখ' },
            ].map(({ key, label, ph }) => (
              <div key={key}>
                <label className="block text-xs text-slate-500 mb-1">{label}</label>
                <input
                  className="input text-sm py-1.5"
                  placeholder={ph}
                  value={(filters[key as keyof SearchFilters] as string) || ''}
                  onChange={(e) => setFilter(key as keyof SearchFilters, e.target.value)}
                />
              </div>
            ))}
          </div>
          <div className="flex gap-2 mt-3">
            <button onClick={clearFilters} className="btn-secondary text-xs flex items-center gap-1.5">
              <X className="w-3.5 h-3.5" /> ফিল্টার মুছুন
            </button>
            <div className="flex gap-1 ml-auto">
              {(['csv', 'excel', 'json'] as const).map((fmt) => (
                <button
                  key={fmt}
                  onClick={() => exportMutation.mutate(fmt)}
                  disabled={exportMutation.isPending}
                  className="btn-secondary text-xs flex items-center gap-1"
                >
                  {exportMutation.isPending && exportMutation.variables === fmt
                    ? <Loader2 className="w-3 h-3 animate-spin" />
                    : <Download className="w-3 h-3" />
                  }
                  {fmt.toUpperCase()}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Results table */}
      {!data && !isFetching && (
        <div className="card p-12 text-center">
          <Search className="w-10 h-10 text-slate-600 mx-auto mb-3" />
          <p className="text-slate-400">উপরের বক্সে টাইপ করে অনুসন্ধান শুরু করুন</p>
          <p className="text-slate-600 text-sm mt-1">নাম, পিতার নাম, ভোটার নম্বর, জেলা ইত্যাদি দিয়ে খুঁজুন</p>
        </div>
      )}

      {data && data.total === 0 && (
        <div className="card p-12 text-center">
          <Filter className="w-10 h-10 text-slate-600 mx-auto mb-3" />
          <p className="text-slate-400">কোনো ফলাফল পাওয়া যায়নি</p>
          <p className="text-slate-600 text-sm mt-1">অনুসন্ধানের শব্দ পরিবর্তন করে আবার চেষ্টা করুন</p>
        </div>
      )}

      {hasResults && (
        <>
          <div className="table-container">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-700 bg-slate-800/50">
                  {['#', 'নাম', 'পিতার নাম', 'ভোটার নম্বর', 'উপজেলা', 'জেলা', 'জন্মতারিখ', ''].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-medium text-slate-400 whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.items.map((record) => (
                  <tr
                    key={record.id}
                    className="table-row cursor-pointer"
                    onClick={() => setSelectedRecord(record)}
                  >
                    <td className="px-4 py-3 text-slate-500 font-mono text-xs">{record.id}</td>
                    <td className="px-4 py-3 text-slate-200 bengali font-medium max-w-[140px] truncate">
                      {record.name || '—'}
                    </td>
                    <td className="px-4 py-3 text-slate-300 bengali max-w-[140px] truncate">
                      {record.father_name || '—'}
                    </td>
                    <td className="px-4 py-3 text-slate-400 font-mono text-xs">
                      {record.voter_id || '—'}
                    </td>
                    <td className="px-4 py-3 text-slate-400 bengali max-w-[100px] truncate">
                      {record.upazila || '—'}
                    </td>
                    <td className="px-4 py-3 text-slate-400 bengali max-w-[100px] truncate">
                      {record.district || '—'}
                    </td>
                    <td className="px-4 py-3 text-slate-500 text-xs whitespace-nowrap">
                      {record.birth_date || '—'}
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs text-sky-400 hover:text-sky-300">বিস্তারিত →</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between text-sm">
            <p className="text-slate-400">
              {((filters.page! - 1) * PAGE_SIZE) + 1}–{Math.min(filters.page! * PAGE_SIZE, data.total)} / {data.total.toLocaleString()}
            </p>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setFilters((p) => ({ ...p, page: Math.max(1, (p.page || 1) - 1) }))}
                disabled={filters.page === 1}
                className="btn-secondary px-2 py-1.5 disabled:opacity-40"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="px-3 py-1.5 text-slate-400">
                পৃষ্ঠা {filters.page} / {totalPages}
              </span>
              <button
                onClick={() => setFilters((p) => ({ ...p, page: Math.min(totalPages, (p.page || 1) + 1) }))}
                disabled={filters.page === totalPages}
                className="btn-secondary px-2 py-1.5 disabled:opacity-40"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </>
      )}

      {selectedRecord && (
        <RecordDetail record={selectedRecord} onClose={() => setSelectedRecord(null)} />
      )}
    </div>
  )
}
