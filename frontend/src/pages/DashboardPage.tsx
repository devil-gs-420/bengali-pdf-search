import { useQuery } from '@tanstack/react-query'
import {
  FileText, Users, Search, HardDrive, TrendingUp,
  CheckCircle2, XCircle, Clock, AlertCircle, BarChart3
} from 'lucide-react'
import { statsAPI } from '@/utils/api'
import { SystemStats } from '@/types'
import { Link } from 'react-router-dom'

function StatCard({ icon: Icon, label, value, sub, color }: {
  icon: React.ElementType; label: string; value: string | number
  sub?: string; color: string
}) {
  return (
    <div className="card p-5 flex items-start gap-4 hover:border-slate-600/50 transition-colors">
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${color}`}>
        <Icon className="w-5 h-5" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-2xl font-bold text-white">{typeof value === 'number' ? value.toLocaleString() : value}</p>
        <p className="text-sm text-slate-400 mt-0.5">{label}</p>
        {sub && <p className="text-xs text-slate-600 mt-1">{sub}</p>}
      </div>
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    completed: 'badge-success', failed: 'badge-error',
    processing: 'badge-warning', started: 'badge-info', pending: 'badge-muted'
  }
  const labels: Record<string, string> = {
    completed: 'সম্পন্ন', failed: 'ব্যর্থ',
    processing: 'প্রক্রিয়াধীন', started: 'শুরু', pending: 'অপেক্ষমান'
  }
  return <span className={map[status] || 'badge-muted'}>{labels[status] || status}</span>
}

export default function DashboardPage() {
  const { data, isLoading } = useQuery<SystemStats>({
    queryKey: ['stats'],
    queryFn: () => statsAPI.getStats().then((r) => r.data),
    refetchInterval: 30_000,
  })

  if (isLoading) return (
    <div className="p-6 space-y-6 animate-pulse">
      <div className="h-8 w-48 skeleton rounded" />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(8)].map((_, i) => <div key={i} className="h-24 skeleton rounded-xl" />)}
      </div>
    </div>
  )

  const s = data!

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">ড্যাশবোর্ড</h1>
          <p className="text-sm text-slate-400 mt-0.5">বাংলা PDF সার্চ সিস্টেম</p>
        </div>
        <Link to="/upload" className="btn-primary text-sm flex items-center gap-2">
          <FileText className="w-4 h-4" /> PDF আপলোড
        </Link>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={FileText} label="মোট ডকুমেন্ট" value={s.total_documents}
          color="bg-sky-500/15 text-sky-400" />
        <StatCard icon={Users} label="মোট রেকর্ড" value={s.total_records}
          color="bg-emerald-500/15 text-emerald-400" />
        <StatCard icon={Search} label="মোট অনুসন্ধান" value={s.total_searches}
          color="bg-violet-500/15 text-violet-400" />
        <StatCard icon={HardDrive} label="স্টোরেজ ব্যবহার" value={`${s.storage_used_mb} MB`}
          color="bg-amber-500/15 text-amber-400" />
        <StatCard icon={CheckCircle2} label="সম্পন্ন" value={s.completed_documents}
          color="bg-emerald-500/15 text-emerald-400" />
        <StatCard icon={Clock} label="প্রক্রিয়াধীন" value={s.processing_documents + s.pending_documents}
          color="bg-amber-500/15 text-amber-400" />
        <StatCard icon={XCircle} label="ব্যর্থ" value={s.failed_documents}
          color="bg-red-500/15 text-red-400" />
        <StatCard icon={TrendingUp} label="আজকের আপলোড" value={s.recent_uploads}
          sub="গত ২৪ ঘণ্টায়" color="bg-sky-500/15 text-sky-400" />
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Top Districts */}
        <div className="card p-5">
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 className="w-4 h-4 text-sky-400" />
            <h2 className="text-sm font-semibold text-slate-200">শীর্ষ জেলা (রেকর্ড অনুযায়ী)</h2>
          </div>
          {s.top_districts.length === 0 ? (
            <p className="text-slate-500 text-sm py-4 text-center">কোনো ডেটা নেই</p>
          ) : (
            <div className="space-y-2">
              {s.top_districts.slice(0, 8).map(({ district, count }, i) => {
                const max = s.top_districts[0]?.count || 1
                const pct = Math.round((count / max) * 100)
                return (
                  <div key={district} className="flex items-center gap-3">
                    <span className="text-xs text-slate-600 w-4 shrink-0">{i + 1}</span>
                    <span className="text-sm text-slate-300 w-32 truncate bengali">{district}</span>
                    <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-sky-500 rounded-full transition-all duration-500"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span className="text-xs text-slate-400 w-12 text-right">{count.toLocaleString()}</span>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Recent Activity */}
        <div className="card p-5">
          <div className="flex items-center gap-2 mb-4">
            <AlertCircle className="w-4 h-4 text-sky-400" />
            <h2 className="text-sm font-semibold text-slate-200">সাম্প্রতিক আপলোড</h2>
          </div>
          {s.recent_activity.length === 0 ? (
            <p className="text-slate-500 text-sm py-4 text-center">কোনো আপলোড নেই</p>
          ) : (
            <div className="space-y-2">
              {s.recent_activity.map((a) => (
                <div key={a.session_id} className="flex items-center gap-3 py-2 border-b border-slate-700/40 last:border-0">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-slate-300 truncate">{a.folder_name || 'Upload'}</p>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {a.processed_files}/{a.total_files} ফাইল · {a.total_records} রেকর্ড
                    </p>
                  </div>
                  <StatusBadge status={a.status} />
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { to: '/search', label: 'নাম দিয়ে খুঁজুন', desc: 'অনুসন্ধান করুন' },
          { to: '/upload', label: 'PDF আপলোড', desc: 'নতুন ফাইল যোগ করুন' },
          { to: '/documents', label: 'সব ডকুমেন্ট', desc: 'তালিকা দেখুন' },
          { to: '/search?q=', label: 'এক্সপোর্ট', desc: 'ডেটা ডাউনলোড' },
        ].map(({ to, label, desc }) => (
          <Link key={to} to={to}
            className="card p-4 hover:border-sky-500/30 hover:bg-sky-500/5 transition-all cursor-pointer text-center">
            <p className="text-sm font-medium text-slate-200">{label}</p>
            <p className="text-xs text-slate-500 mt-1">{desc}</p>
          </Link>
        ))}
      </div>
    </div>
  )
}
