import { useEffect, useMemo, useRef, useState } from 'react';
import { AUTH_API_URL, AuthScreen, UserManagement, apiError, toSessionUser, type SessionUser } from './auth';
import { getMessages, type Language } from './i18n';

type ReplaySpeed = 1 | 2 | 5 | 10 | 50 | 100 | 250;
type ReplayEvent = {
  sequence: number;
  time_seconds: number;
  amount: number;
  model: 'xgboost' | 'random_forest';
  fraud_probability: number;
  is_fraud: boolean;
  threshold: number;
  latency_ms: number;
  pca_features: Record<string, number>;
};

type ReplayComplete = { type: 'complete'; emitted: number; acknowledged: number; dropped: number };
type DashboardView = 'monitor' | 'users';

const WS_URL = import.meta.env.VITE_REPLAY_WS_URL ?? 'ws://localhost:8000/api/v1/replay/ws';
const SPEEDS: ReplaySpeed[] = [1, 2, 5, 10, 50, 100, 250];

function AlertExplanation({ event }: { event: ReplayEvent }) {
  const [data, setData] = useState<{ base_value: number; top_contributions: { feature: string; value: number; direction: string }[] } | null>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    const controller = new AbortController();
    setData(null); setError('');
    const api = import.meta.env.VITE_FRAUD_API_URL ?? 'http://localhost:8000';
    fetch(`${api}/api/v1/replay/${event.sequence}/explain?model=${encodeURIComponent(event.model)}&top_n=10`, { signal: controller.signal })
      .then(async (response) => { if (!response.ok) throw new Error(`Explanation unavailable (${response.status})`); return response.json(); })
      .then(setData).catch((reason) => { if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'Explanation unavailable'); });
    return () => controller.abort();
  }, [event.sequence, event.model]);
  const maximum = Math.max(...(data?.top_contributions.map((item) => Math.abs(item.value)) ?? []), 0.0000001);
  return <section className="mt-8" aria-label="SHAP feature contributions"><h3 className="text-sm font-semibold text-white">SHAP feature contributions</h3><p className="mt-2 text-xs text-slate-400">Signed contributions in the explainer’s output units; positive values increase the model output.</p>{error ? <p role="alert" className="mt-3 text-sm text-rose-300">{error}</p> : !data ? <p className="mt-3 text-sm text-slate-400">Loading explanation…</p> : <><p className="mt-3 text-xs text-slate-400">Base value: {data.base_value.toFixed(4)}</p><ul className="mt-4 space-y-3">{data.top_contributions.map((item) => <li key={item.feature} title={`${item.feature}: ${item.value.toFixed(5)} (${item.direction})`}><div className="flex justify-between text-xs text-slate-200"><span>{item.feature}</span><span>{item.value >= 0 ? '+' : ''}{item.value.toFixed(4)}</span></div><div className="mt-1 h-2 rounded bg-slate-800"><div className={`h-2 rounded ${item.value >= 0 ? 'bg-rose-400' : 'bg-cyan-300'}`} style={{ width: `${Math.abs(item.value) / maximum * 100}%` }} /></div></li>)}</ul></>}</section>;
}

function percentile(values: number[], percentileValue: number): number {
  if (!values.length) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const index = Math.min(sorted.length - 1, Math.ceil((percentileValue / 100) * sorted.length) - 1);
  return sorted[Math.max(0, index)];
}

function riskLabel(event: ReplayEvent): string {
  if (event.fraud_probability >= Math.max(event.threshold, 0.85)) return 'HIGH RISK';
  if (event.is_fraud) return 'REVIEW';
  return 'CLEAR';
}

function DashboardSidebar({
  currentUser,
  view,
  canManageUsers,
  connected,
  onViewChange,
  onLogout,
  language,
}: {
  currentUser: SessionUser;
  view: DashboardView;
  canManageUsers: boolean;
  connected: boolean;
  onViewChange: (view: DashboardView) => void;
  onLogout: () => void;
  language: Language;
}) {
  const kh = language === 'km';
  return (
    <aside className="sticky top-0 flex h-screen w-[248px] shrink-0 flex-col border-r border-slate-800 bg-[#0a1724] px-4 py-6 max-lg:hidden">
      <div className="flex items-center gap-3 px-3">
        <span className="grid h-9 w-9 place-items-center rounded-xl bg-cyan-300 text-lg font-black text-[#08131f]">◈</span>
        <div><p className="text-sm font-bold tracking-tight text-white">Transfer<span className="text-cyan-300">Guard</span></p><p className="mt-0.5 text-[9px] font-bold uppercase tracking-[0.18em] text-slate-500">Fraud operations</p></div>
      </div>
      <p className="mb-3 mt-12 px-3 text-[10px] font-bold uppercase tracking-[0.2em] text-slate-600">{kh ? 'កន្លែងធ្វើការ' : 'Workspace'}</p>
      <nav className="space-y-1">
        <button onClick={() => onViewChange('monitor')} className={`flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-sm font-semibold transition ${view === 'monitor' ? 'bg-cyan-300/10 text-cyan-200' : 'text-slate-500 hover:bg-slate-800/70 hover:text-slate-200'}`}><span className="text-base">▦</span>{kh ? 'តាមដានផ្ទាល់' : 'Live monitor'}</button>
        {canManageUsers && <button onClick={() => onViewChange('users')} className={`flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-sm font-semibold transition ${view === 'users' ? 'bg-cyan-300/10 text-cyan-200' : 'text-slate-500 hover:bg-slate-800/70 hover:text-slate-200'}`}><span className="text-base">♙</span>{getMessages(language).userManagement}</button>}
      </nav>
      <div className="dashboard-sidebar-bottom mt-auto space-y-4">
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-3"><div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-wider text-slate-500"><span className={`h-2 w-2 rounded-full ${connected ? 'bg-emerald-300' : 'bg-slate-600'}`} />{connected ? 'Stream connected' : 'Stream offline'}</div><p className="mt-2 text-[11px] leading-5 text-slate-600">WebSocket replay channel</p></div>
        <div className="flex items-center gap-3 border-t border-slate-800 pt-4"><span className="grid h-9 w-9 place-items-center rounded-full bg-violet-300/20 text-xs font-bold text-violet-200">{currentUser.name.slice(0, 2).toUpperCase()}</span><div className="min-w-0 flex-1"><p className="truncate text-xs font-semibold text-slate-200">{currentUser.name}</p><p className="truncate text-[10px] text-slate-500">{currentUser.role}</p></div></div>
        <button type="button" onClick={onLogout} className="sidebar-logout">{kh ? 'ចាកចេញ' : 'Log out'}</button>
      </div>
    </aside>
  );
}

function HeaderPreferences({ theme, language, onThemeChange, onLanguageChange }: { theme: 'dark' | 'light'; language: Language; onThemeChange: () => void; onLanguageChange: (language: Language) => void }) {
  return (
    <div className="dashboard-preferences" aria-label="Display preferences">
      <div className="dashboard-language-switch" role="group" aria-label="Language">
        <button type="button" className={language === 'en' ? 'is-active' : ''} onClick={() => onLanguageChange('en')}>EN</button>
        <button type="button" className={language === 'km' ? 'is-active' : ''} onClick={() => onLanguageChange('km')}>KH</button>
      </div>
      <button type="button" className="dashboard-theme-switch" onClick={onThemeChange} aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}><span aria-hidden="true">{theme === 'dark' ? '☼' : '☾'}</span><span>{theme === 'dark' ? 'Light' : 'Dark'}</span></button>
    </div>
  );
}

export default function LiveDashboard() {
  const [currentUser, setCurrentUser] = useState<SessionUser | null>(() => {
    const stored = sessionStorage.getItem('transferguard-user');
    return stored ? JSON.parse(stored) as SessionUser : null;
  });
  const [authToken, setAuthToken] = useState(() => sessionStorage.getItem('transferguard-token') ?? '');
  const [refreshToken, setRefreshToken] = useState(() => sessionStorage.getItem('transferguard-refresh-token') ?? '');
  const [language, setLanguage] = useState<Language>(() => localStorage.getItem('transferguard-language') === 'km' ? 'km' : 'en');
  const t = getMessages(language);
  const kh = language === 'km';
  const [theme, setTheme] = useState<'dark' | 'light'>(() => localStorage.getItem('transferguard-dashboard-theme') === 'light' ? 'light' : 'dark');
  const [view, setView] = useState<DashboardView>('monitor');
  const [events, setEvents] = useState<ReplayEvent[]>([]);
  const [speed, setSpeed] = useState<ReplaySpeed>(10);
  const [model, setModel] = useState<'xgboost' | 'random_forest'>('xgboost');
  const [connected, setConnected] = useState(false);
  const [running, setRunning] = useState(false);
  const [completion, setCompletion] = useState<ReplayComplete | null>(null);
  const [selected, setSelected] = useState<ReplayEvent | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const startedAtRef = useRef<number | null>(null);
  const canManageUsers = currentUser?.role === 'admin' || currentUser?.role === 'super_admin';
  useEffect(() => { localStorage.setItem('transferguard-dashboard-theme', theme); }, [theme]);
  useEffect(() => { localStorage.setItem('transferguard-language', language); document.documentElement.lang = language; }, [language]);
  useEffect(() => {
    function syncSession() {
      const stored = sessionStorage.getItem('transferguard-user');
      setCurrentUser(stored ? JSON.parse(stored) as SessionUser : null);
      setAuthToken(sessionStorage.getItem('transferguard-token') ?? '');
      setRefreshToken(sessionStorage.getItem('transferguard-refresh-token') ?? '');
    }
    window.addEventListener('transferguard-session-updated', syncSession);
    return () => window.removeEventListener('transferguard-session-updated', syncSession);
  }, []);

  async function login(email: string, password: string) {
    const response = await fetch(`${AUTH_API_URL}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: email.trim(), password }),
    });
    if (!response.ok) throw await apiError(response, 'Unable to sign in');
    const data = await response.json() as { access_token: string; refresh_token: string; user: Parameters<typeof toSessionUser>[0] };
    const user = toSessionUser(data.user);
    setCurrentUser(user);
    setAuthToken(data.access_token);
    setRefreshToken(data.refresh_token);
    sessionStorage.setItem('transferguard-token', data.access_token);
    sessionStorage.setItem('transferguard-refresh-token', data.refresh_token);
    sessionStorage.setItem('transferguard-user', JSON.stringify(user));
  }

  async function logout() {
    if (authToken) {
      await fetch(`${AUTH_API_URL}/api/v1/auth/logout`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${authToken}`, 'Content-Type': 'application/json' },
        body: refreshToken ? JSON.stringify({ refresh_token: refreshToken }) : undefined,
      }).catch(() => undefined);
    }
    stopReplay();
    sessionStorage.removeItem('transferguard-token');
    sessionStorage.removeItem('transferguard-refresh-token');
    sessionStorage.removeItem('transferguard-user');
    setAuthToken('');
    setRefreshToken('');
    setCurrentUser(null);
    setView('monitor');
  }

  const metrics = useMemo(() => {
    const elapsedSeconds = startedAtRef.current ? Math.max(0.001, (Date.now() - startedAtRef.current) / 1000) : 0;
    const latencyValues = events.map((event) => event.latency_ms);
    return {
      txPerSecond: elapsedSeconds ? events.length / elapsedSeconds : 0,
      p95: percentile(latencyValues, 95),
      reviewQueue: events.filter((event) => event.is_fraud).length,
      highRisk: events.filter((event) => riskLabel(event) === 'HIGH RISK').length,
    };
  }, [events]);

  useEffect(() => () => socketRef.current?.close(), []);

  function stopReplay() {
    socketRef.current?.close();
    socketRef.current = null;
    setConnected(false);
    setRunning(false);
  }

  function startReplay() {
    stopReplay();
    setEvents([]);
    setCompletion(null);
    startedAtRef.current = Date.now();
    const socket = new WebSocket(WS_URL);
    socketRef.current = socket;
    socket.onopen = () => {
      setConnected(true);
      setRunning(true);
      socket.send(JSON.stringify({ speed, model }));
    };
    socket.onmessage = (message) => {
      const payload = JSON.parse(message.data) as ReplayEvent | ReplayComplete;
      if (payload.type === 'complete') {
        setCompletion(payload);
        setRunning(false);
        return;
      }
      setEvents((current) => [...current.slice(-199), payload]);
      socket.send(JSON.stringify({ type: 'ack', sequence: payload.sequence }));
    };
    socket.onerror = () => setRunning(false);
    socket.onclose = () => {
      setConnected(false);
      setRunning(false);
    };
  }

  if (!currentUser) return <AuthScreen language={language} onAuthenticate={login} />;

  if (view === 'users' && canManageUsers) {
    return (
      <div className={`dashboard-shell flex min-h-screen bg-[#08131f] text-slate-100 ${theme === 'light' ? 'dashboard-theme-light' : ''}`}>
        <DashboardSidebar currentUser={currentUser} view={view} canManageUsers={canManageUsers} connected={connected} onViewChange={setView} onLogout={() => void logout()} language={language} />
        <main className="min-w-0 flex-1 px-5 py-7 sm:px-8 lg:px-10">
        <button type="button" onClick={() => void logout()} className="mobile-logout">Log out</button>
        <div className="mx-auto max-w-[1480px]">
          <header className="dashboard-page-header mb-8 flex items-center justify-between gap-4">
            <div><p className="text-[11px] font-bold uppercase tracking-[0.28em] text-cyan-300">TransferGuard / {kh ? 'រដ្ឋបាល' : 'administration'}</p><h1 className="mt-3 text-3xl font-semibold text-white">{t.userManagement}</h1><p className="mt-2 text-sm text-slate-400">{kh ? 'គ្រប់គ្រងតួនាទី សិទ្ធិ និងស្ថានភាពគណនី។' : 'Manage roles, access, and account status.'}</p></div>
            <div className="dashboard-header-actions"><div className="dashboard-header-utility"><HeaderPreferences theme={theme} language={language} onThemeChange={() => setTheme((current) => current === 'dark' ? 'light' : 'dark')} onLanguageChange={setLanguage} /><button onClick={() => setView('monitor')} className="rounded-lg border border-slate-700 px-4 py-2 text-xs font-semibold text-slate-300 hover:border-cyan-300 hover:text-cyan-200">Live monitor</button></div></div>
          </header>
          <UserManagement currentUser={currentUser} language={language} token={authToken} />
        </div>
        </main>
      </div>
    );
  }

  return (
    <div className={`dashboard-shell flex min-h-screen bg-[#08131f] text-slate-100 selection:bg-cyan-300 selection:text-[#08131f] ${theme === 'light' ? 'dashboard-theme-light' : ''}`}>
      <DashboardSidebar currentUser={currentUser} view={view} canManageUsers={canManageUsers} connected={connected} onViewChange={setView} onLogout={() => void logout()} language={language} />
      <main className="min-w-0 flex-1">
      <button type="button" onClick={() => void logout()} className="mobile-logout">Log out</button>
      <div className="mx-auto max-w-[1480px] px-5 py-7 sm:px-8 lg:px-10">
        <header className="dashboard-page-header mb-8 flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
          <div>
            <p className="mb-3 text-[11px] font-bold uppercase tracking-[0.28em] text-cyan-300">TransferGuard / live operations</p>
            <h1 className="text-3xl font-semibold tracking-tight text-white sm:text-4xl">{kh ? 'លំហូរប្រតិបត្តិការក្លែងបន្លំកាតឥណទាន' : 'Credit-card fraud stream'}</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">{kh ? 'ចាក់ប្រតិបត្តិការសាកល្បងតាមពេលវេលា ដោយប្រើគំរូ XGBoost និង Random Forest។' : 'Chronological held-out replay with calibrated XGBoost and Random Forest scoring.'}</p>
          </div>
          <div className="dashboard-header-actions"><div className="dashboard-header-utility"><HeaderPreferences theme={theme} language={language} onThemeChange={() => setTheme((current) => current === 'dark' ? 'light' : 'dark')} onLanguageChange={setLanguage} /></div><div className="dashboard-header-run"><span className={`dashboard-stream-status inline-flex items-center gap-2 rounded-full border px-3 py-2 text-xs font-semibold ${connected ? 'border-emerald-400/30 bg-emerald-400/10 text-emerald-300' : 'border-slate-700 bg-slate-900 text-slate-400'}`}><span className={`h-2 w-2 rounded-full ${connected ? 'bg-emerald-300 shadow-[0_0_12px_#6ee7b7]' : 'bg-slate-600'}`} />{connected ? 'Stream connected' : 'Stream offline'}</span><select value={model} onChange={(event) => setModel(event.target.value as typeof model)} className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-200 outline-none focus:border-cyan-300"><option value="xgboost">XGBoost</option><option value="random_forest">Random Forest</option></select><button onClick={running ? stopReplay : startReplay} className={`rounded-lg px-4 py-2 text-xs font-bold transition ${running ? 'border border-rose-400/40 bg-rose-400/10 text-rose-200' : 'bg-cyan-300 text-[#08131f] hover:bg-cyan-200'}`}>{running ? 'Stop replay' : 'Start replay'}</button></div></div>
        </header>

        <section className="mb-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {[
            ['TX / SEC', metrics.txPerSecond.toFixed(1), 'live throughput', 'text-cyan-300'],
            ['P95 LATENCY', `${metrics.p95.toFixed(2)} ms`, 'model scoring', 'text-violet-300'],
            ['REVIEW QUEUE', metrics.reviewQueue.toString(), 'threshold crossings', 'text-amber-300'],
            ['HIGH-RISK ALERTS', metrics.highRisk.toString(), 'probability ≥ 85%', 'text-rose-300'],
          ].map(([label, value, detail, color]) => (
            <article key={label} className="dashboard-card rounded-2xl border border-slate-800 bg-[#0d1d2c] p-5 shadow-2xl shadow-black/10">
              <div className="flex items-center justify-between"><p className="text-[10px] font-bold tracking-[0.2em] text-slate-500">{label}</p><span className={`h-2 w-2 rounded-full bg-current ${color}`} /></div>
              <p className={`mt-4 text-3xl font-semibold tracking-tight ${color}`}>{value}</p>
              <p className="mt-1 text-xs text-slate-500">{detail}</p>
            </article>
          ))}
        </section>

        <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_310px]">
          <article className="dashboard-card dashboard-feed overflow-hidden rounded-2xl border border-slate-800 bg-[#0d1d2c]">
            <div className="flex flex-col justify-between gap-4 border-b border-slate-800 px-5 py-4 sm:flex-row sm:items-center">
              <div><h2 className="text-sm font-semibold text-white">{kh ? 'ប្រតិបត្តិការផ្ទាល់' : 'Live transaction feed'}</h2><p className="mt-1 text-xs text-slate-500">{kh ? 'ចុចប្រតិបត្តិការដែលបានសម្គាល់ ដើម្បីពិនិត្យព័ត៌មាន។' : 'Click a flagged transaction to inspect the scoring payload.'}</p></div>
              <div className="flex items-center gap-2 text-[11px] text-slate-500"><span>Replay speed</span>{SPEEDS.map((value) => <button key={value} disabled={running} onClick={() => setSpeed(value)} className={`rounded-md border px-2 py-1 font-semibold ${speed === value ? 'border-cyan-300/50 bg-cyan-300/10 text-cyan-200' : 'border-slate-700 text-slate-500 hover:text-slate-300'}`}>{value}</button>)}</div>
            </div>
            <div className="max-h-[600px] overflow-auto">
              <table className="w-full min-w-[760px] text-left text-xs">
                <thead className="sticky top-0 bg-[#0d1d2c] text-[10px] uppercase tracking-[0.18em] text-slate-500"><tr><th className="px-5 py-3">Seq / time</th><th className="px-4 py-3">Amount</th><th className="px-4 py-3">Risk score</th><th className="px-4 py-3">Latency</th><th className="px-5 py-3">Status</th></tr></thead>
                <tbody className="divide-y divide-slate-800/80">{events.length ? events.slice().reverse().map((event) => { const label = riskLabel(event); return <tr key={event.sequence} onClick={() => label !== 'CLEAR' && setSelected(event)} className={`${label !== 'CLEAR' ? 'cursor-pointer hover:bg-slate-800/60' : ''}`}><td className="px-5 py-3"><span className="font-semibold text-slate-300">#{event.sequence.toString().padStart(5, '0')}</span><span className="ml-2 text-slate-500">{event.time_seconds.toFixed(0)}s</span></td><td className="px-4 py-3 text-slate-300">${event.amount.toFixed(2)}</td><td className="px-4 py-3"><div className="flex items-center gap-2"><div className="h-1.5 w-20 rounded-full bg-slate-800"><div className={`h-1.5 rounded-full ${label === 'HIGH RISK' ? 'bg-rose-400' : label === 'REVIEW' ? 'bg-amber-300' : 'bg-emerald-300'}`} style={{ width: `${Math.min(100, event.fraud_probability * 100)}%` }} /></div><span className="font-mono text-slate-300">{(event.fraud_probability * 100).toFixed(1)}%</span></div></td><td className="px-4 py-3 font-mono text-slate-500">{event.latency_ms.toFixed(2)}ms</td><td className="px-5 py-3"><span className={`rounded-full px-2 py-1 text-[10px] font-bold ${label === 'HIGH RISK' ? 'bg-rose-400/15 text-rose-300' : label === 'REVIEW' ? 'bg-amber-300/15 text-amber-200' : 'bg-emerald-300/10 text-emerald-300'}`}>{label}</span></td></tr>; }) : <tr><td colSpan={5} className="px-5 py-20 text-center text-slate-600">Start a replay to populate the live feed.</td></tr>}</tbody>
              </table>
            </div>
          </article>

          <aside className="dashboard-card dashboard-delivery rounded-2xl border border-slate-800 bg-[#0d1d2c] p-5"><div className="flex items-center justify-between"><h2 className="text-sm font-semibold text-white">Delivery monitor</h2><span className="text-[10px] font-bold uppercase tracking-widest text-emerald-300">ACKED</span></div><div className="mt-6 space-y-4 text-xs"><div className="flex justify-between text-slate-500"><span>Events displayed</span><strong className="text-slate-200">{events.length}</strong></div><div className="flex justify-between text-slate-500"><span>Last sequence</span><strong className="text-slate-200">{events.at(-1)?.sequence ?? '—'}</strong></div><div className="flex justify-between text-slate-500"><span>Dropped messages</span><strong className="text-emerald-300">{completion?.dropped ?? 0}</strong></div></div>{completion && <div className="mt-6 rounded-xl border border-emerald-400/20 bg-emerald-400/5 p-3 text-xs text-emerald-200">Replay complete: {completion.acknowledged}/{completion.emitted} events acknowledged.</div>}<p className="mt-8 text-xs leading-5 text-slate-500">Every WebSocket event is acknowledged by sequence number before the next event is released.</p></aside>
        </section>
      </div>

      {selected && <div className="fixed inset-0 z-20 bg-black/60 backdrop-blur-sm" onClick={() => setSelected(null)}><aside className="absolute right-0 top-0 h-full w-full max-w-md overflow-y-auto border-l border-slate-700 bg-[#0b1a28] p-6 shadow-2xl" onClick={(event) => event.stopPropagation()}><div className="flex items-start justify-between"><div><p className="text-[10px] font-bold uppercase tracking-[0.2em] text-rose-300">Flagged transaction</p><h2 className="mt-2 text-2xl font-semibold text-white">#{selected.sequence.toString().padStart(5, '0')}</h2></div><button onClick={() => setSelected(null)} aria-label="Close inspection" className="rounded-lg border border-slate-700 px-3 py-1 text-xl text-slate-400 hover:text-white">×</button></div><div className="mt-8 grid grid-cols-2 gap-3">{[['Risk probability', `${(selected.fraud_probability * 100).toFixed(2)}%`], ['Decision threshold', `${(selected.threshold * 100).toFixed(0)}%`], ['Amount', `$${selected.amount.toFixed(2)}`], ['Score latency', `${selected.latency_ms.toFixed(2)} ms`]].map(([label, value]) => <div key={label} className="rounded-xl border border-slate-800 bg-slate-900/60 p-3"><p className="text-[10px] uppercase tracking-wider text-slate-500">{label}</p><p className="mt-2 font-mono text-sm text-slate-200">{value}</p></div>)}</div><AlertExplanation event={selected} /><div className="mt-8"><h3 className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Top PCA signal inputs</h3><div className="mt-3 divide-y divide-slate-800 rounded-xl border border-slate-800">{Object.entries(selected.pca_features).map(([feature, value]) => <div key={feature} className="flex justify-between px-4 py-3 text-sm"><span className="font-mono text-cyan-200">{feature}</span><span className="font-mono text-slate-300">{value.toFixed(5)}</span></div>)}</div></div><p className="mt-8 text-xs leading-5 text-slate-500">Model: {selected.model}. Time: {selected.time_seconds.toFixed(0)} seconds in the held-out chronological test stream.</p></aside></div>}
      </main>
    </div>
  );
}
