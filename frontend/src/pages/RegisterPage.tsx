import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { BookOpen, Loader2 } from 'lucide-react'
import { authAPI } from '@/utils/api'
import toast from 'react-hot-toast'

export default function RegisterPage() {
  const navigate = useNavigate()
  const [form, setForm] = useState({ email: '', username: '', password: '', full_name: '' })
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      await authAPI.register(form)
      toast.success('নিবন্ধন সফল! এখন লগইন করুন।')
      navigate('/login')
    } catch {
    } finally {
      setLoading(false)
    }
  }

  const field = (key: keyof typeof form, label: string, type = 'text', placeholder = '') => (
    <div>
      <label className="block text-sm text-slate-400 mb-1.5">{label}</label>
      <input
        type={type}
        className="input"
        placeholder={placeholder}
        value={form[key]}
        onChange={(e) => setForm({ ...form, [key]: e.target.value })}
        required={key !== 'full_name'}
      />
    </div>
  )

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-sky-500/15 border border-sky-500/30 mb-4">
            <BookOpen className="w-7 h-7 text-sky-400" />
          </div>
          <h1 className="text-2xl font-bold text-white">নতুন অ্যাকাউন্ট</h1>
          <p className="text-slate-400 text-sm mt-1">বাংলা PDF সার্চ সিস্টেমে যোগ দিন</p>
        </div>

        <div className="card p-6 space-y-4">
          <form onSubmit={handleSubmit} className="space-y-4">
            {field('full_name', 'পূর্ণ নাম (ঐচ্ছিক)', 'text', 'আপনার নাম')}
            {field('username', 'ইউজারনেম', 'text', 'username')}
            {field('email', 'ইমেইল', 'email', 'your@email.com')}
            {field('password', 'পাসওয়ার্ড (কমপক্ষে ৮ অক্ষর)', 'password', '••••••••')}

            <button type="submit" className="btn-primary w-full flex items-center justify-center gap-2" disabled={loading}>
              {loading && <Loader2 className="w-4 h-4 animate-spin" />}
              {loading ? 'নিবন্ধন হচ্ছে...' : 'নিবন্ধন করুন'}
            </button>
          </form>

          <p className="text-center text-sm text-slate-500">
            ইতিমধ্যে অ্যাকাউন্ট আছে?{' '}
            <Link to="/login" className="text-sky-400 hover:text-sky-300 transition-colors">
              লগইন করুন
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
