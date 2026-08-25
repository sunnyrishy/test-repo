import { Link, Route, Routes } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import JobDetail from './pages/JobDetail'
import Stats from './pages/Stats'

export default function App() {
  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
          <Link to="/" className="text-sm font-semibold tracking-tight">
            AI Job Intelligence
          </Link>
          <span className="text-xs text-slate-500">Discovery · verification · ranking</span>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-6">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/job/:id" element={<JobDetail />} />
          <Route path="/stats" element={<Stats />} />
        </Routes>
      </main>
    </div>
  )
}
