import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { AUTH_API_URL, AuthScreen, UserManagement, apiError, roleLabel, toSessionUser, type SessionUser } from './auth';
import type { Language } from './i18n';
import './style.css';

type Decision = 'APPROVED' | 'FLAGGED_BY_RULES' | 'FLAGGED_BY_ML';
type Transaction = {
  id?: number;
  transaction_id?: number;
  timestamp?: string;
  amount?: number;
  status: string;
  decision: string;
  risk_score: number;
  reasons: string[];
  confirmed_label?: number | null;
  tier_triggered?: string;
  threshold?: number;
};

type ApiResult = Transaction & { explanations?: string[] };
const API_URL = 'http://localhost:5000';
const defaultVectors = Object.fromEntries(Array.from({ length: 28 }, (_, index) => [`V${index + 1}`, 0]));
const labels = {
  en: {
    workspace: 'HYBRID FRAUD WORKSPACE', overview: 'Overview', score: 'Score a transaction', activity: 'Activity log', users: 'User management', api: 'API connected when app.py is running', eyebrow: 'CREDIT CARD FRAUD · TWO-TIER ENGINE', title: 'Operations overview', subtitle: 'Monitor rule decisions, CatBoost risk, SHAP explanations, and analyst feedback.', newAssessment: '+ New assessment', evaluated: 'Transactions evaluated', blocked: 'Fraud blocked', approval: 'Approval rate', queue: 'Retraining queue', scoreTitle: 'Score a credit-card transaction', scoreSub: 'Stage 1 rules run before CatBoost and SHAP.', amount: 'Transaction amount ($)', time: 'Timestamp in dataset seconds', blacklisted: 'Blacklisted device / IP', analyze: 'Run hybrid assessment →', analyzing: 'Analyzing...', settings: 'Rule & model settings', threshold: 'ML risk threshold', activityTitle: 'Activity log & analyst feedback', activitySub: 'Confirm fraud or mark false positives to build the retraining queue.', confirm: 'Confirm fraud', falsePositive: 'False positive', light: 'Light mode', dark: 'Dark mode', language: 'Language', back: '← Back to overview', logout: 'Log out'
  },
  km: {
    workspace: 'កន្លែងធ្វើការក្លែងបន្លំកូនកាត់', overview: 'ទិដ្ឋភាពទូទៅ', score: 'វាយតម្លៃប្រតិបត្តិការ', activity: 'កំណត់ហេតុសកម្មភាព', users: 'គ្រប់គ្រងអ្នកប្រើ', api: 'API បានភ្ជាប់នៅពេល app.py កំពុងដំណើរការ', eyebrow: 'ក្លែងបន្លំកាតឥណទាន · ម៉ាស៊ីនពីរជាន់', title: 'ទិដ្ឋភាពប្រតិបត្តិការ', subtitle: 'តាមដានច្បាប់ ពិន្ទុ CatBoost ការពន្យល់ SHAP និងមតិយោបល់អ្នកវិភាគ។', newAssessment: '+ វាយតម្លៃថ្មី', evaluated: 'ប្រតិបត្តិការដែលបានវាយតម្លៃ', blocked: 'ការក្លែងបន្លំត្រូវបានទប់ស្កាត់', approval: 'អត្រាអនុម័ត', queue: 'ជួររង់ចាំបណ្តុះបណ្តាលឡើងវិញ', scoreTitle: 'វាយតម្លៃប្រតិបត្តិការកាតឥណទាន', scoreSub: 'ច្បាប់ជាន់ទី១ ដំណើរការមុន CatBoost និង SHAP។', amount: 'ចំនួនប្រតិបត្តិការ ($)', time: 'ពេលវេលាក្នុងវិនាទី', blacklisted: 'ឧបករណ៍ / IP ក្នុងបញ្ជីខ្មៅ', analyze: 'ដំណើរការវាយតម្លៃកូនកាត់ →', analyzing: 'កំពុងវិភាគ...', settings: 'ការកំណត់ច្បាប់ និងម៉ូដែល', threshold: 'កម្រិតហានិភ័យ ML', activityTitle: 'កំណត់ហេតុ និងមតិយោបល់អ្នកវិភាគ', activitySub: 'បញ្ជាក់ការក្លែងបន្លំ ឬសម្គាល់ការជូនដំណឹងខុស ដើម្បីបង្កើតជួរបណ្តុះបណ្តាលឡើងវិញ។', confirm: 'បញ្ជាក់ការក្លែងបន្លំ', falsePositive: 'ជូនដំណឹងខុស', light: 'របៀបភ្លឺ', dark: 'របៀបងងឹត', language: 'ភាសា', back: '← ត្រឡប់ទៅទិដ្ឋភាពទូទៅ', logout: 'ចាកចេញ'
  }
} as const;

function App() {
  const [currentUser, setCurrentUser] = useState<SessionUser | null>(() => {
    const stored = sessionStorage.getItem('transferguard-user');
    return stored ? JSON.parse(stored) as SessionUser : null;
  });
  const [authToken, setAuthToken] = useState(() => sessionStorage.getItem('transferguard-token') ?? '');
  const [refreshToken, setRefreshToken] = useState(() => sessionStorage.getItem('transferguard-refresh-token') ?? '');
  const [language, setLanguage] = useState<Language>(() => localStorage.getItem('transferguard-language') === 'km' ? 'km' : 'en');
  const [theme, setTheme] = useState<'light' | 'dark'>(() => localStorage.getItem('transferguard-theme') === 'dark' ? 'dark' : 'light');
  const copy = labels[language];
  const canManageUsers = currentUser?.role === 'admin' || currentUser?.role === 'super_admin';
  const [route, setRoute] = useState<'overview' | 'score' | 'activity' | 'users'>(() => window.location.hash === '#users' ? 'users' : 'overview');
  const [assessmentOpen, setAssessmentOpen] = useState(false);
  const [amount, setAmount] = useState(1250);
  const [time, setTime] = useState(7200);
  const [blacklisted, setBlacklisted] = useState(false);
  const [threshold, setThreshold] = useState(0.5);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [result, setResult] = useState<ApiResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [retrainingNotice, setRetrainingNotice] = useState('');

  async function refreshTransactions() {
    try {
      const response = await fetch(`${API_URL}/api/v1/transactions`);
      if (response.ok) setTransactions(await response.json());
    } catch {
      // The dashboard remains usable while the API is offline.
    }
  }

  useEffect(() => { void refreshTransactions(); }, []);
  useEffect(() => { document.documentElement.dataset.theme = theme; localStorage.setItem('transferguard-theme', theme); }, [theme]);
  useEffect(() => { document.documentElement.lang = language; localStorage.setItem('transferguard-language', language); }, [language]);
  useEffect(() => {
    const syncRoute = () => {
      const nextRoute = window.location.hash === '#users' ? 'users' : 'overview';
      setRoute(nextRoute === 'users' && !canManageUsers ? 'overview' : nextRoute);
    };
    window.addEventListener('hashchange', syncRoute);
    return () => window.removeEventListener('hashchange', syncRoute);
  }, [currentUser, canManageUsers]);

  async function login(email: string, password: string) {
    const response = await fetch(`${AUTH_API_URL}/api/v1/auth/login`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email: email.trim(), password }) });
    if (!response.ok) throw await apiError(response, 'Unable to sign in');
    const data = await response.json() as { access_token: string; refresh_token: string; user: Parameters<typeof toSessionUser>[0] };
    const user = toSessionUser(data.user);
    setCurrentUser(user);
    setAuthToken(data.access_token);
    setRefreshToken(data.refresh_token);
    sessionStorage.setItem('transferguard-token', data.access_token);
    sessionStorage.setItem('transferguard-refresh-token', data.refresh_token);
    sessionStorage.setItem('transferguard-user', JSON.stringify(user));
    window.location.hash = '#overview';
  }

  async function logout() {
    if (authToken) await fetch(`${AUTH_API_URL}/api/v1/auth/logout`, { method: 'POST', headers: { Authorization: 'Bearer ' + authToken, 'Content-Type': 'application/json' }, body: refreshToken ? JSON.stringify({ refresh_token: refreshToken }) : undefined });
    sessionStorage.removeItem('transferguard-token');
    sessionStorage.removeItem('transferguard-refresh-token');
    sessionStorage.removeItem('transferguard-user');
    setAuthToken('');
    setRefreshToken('');
    setCurrentUser(null);
    window.location.hash = '#login';
    setRoute('overview');
    setAssessmentOpen(false);
    setResult(null);
    setError('');
  }

  async function scoreTransaction(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError('');
    const payload = { Time: time, Amount: amount, is_blacklisted_device: blacklisted ? 1 : 0, ...defaultVectors };
    try {
      const response = await fetch(`${API_URL}/api/v1/predict`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error ?? `API error: ${response.status}`);
      setResult(data);
      await refreshTransactions();
    } catch (err) {
      setError(err instanceof Error ? `${err.message}. Start app.py on port 5000.` : 'Prediction failed');
    } finally { setLoading(false); }
  }

  async function submitFeedback(id: number, label: 0 | 1) {
    await fetch(`${API_URL}/api/v1/transactions/${id}/feedback`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ confirmed_label: label }),
    });
    await refreshTransactions();
  }

  const evaluated = transactions.length;
  const blocked = transactions.filter((item) => item.status === 'REJECTED');
  const ruleBlocked = transactions.filter((item) => item.decision === 'FLAGGED_BY_RULES').length;
  const mlBlocked = transactions.filter((item) => item.decision === 'FLAGGED_BY_ML').length;
  const labeled = transactions.filter((item) => item.confirmed_label !== null && item.confirmed_label !== undefined).length;
  const retrainingTarget = 50;
  const confirmedFraud = transactions.filter((item) => item.confirmed_label === 1).length;
  const falsePositives = transactions.filter((item) => item.confirmed_label === 0).length;
  const pendingReview = transactions.filter((item) => {
    const flagged = item.status === 'REJECTED' || item.decision === 'FLAGGED_BY_RULES' || item.decision === 'FLAGGED_BY_ML';
    return flagged && (item.confirmed_label === null || item.confirmed_label === undefined);
  }).length;
  const retrainingReady = labeled >= retrainingTarget;
  const retrainingProgress = Math.min(100, Math.round((labeled / retrainingTarget) * 100));
  const buckets = useMemo(() => [
    transactions.filter((item) => item.risk_score < 0.2).length,
    transactions.filter((item) => item.risk_score >= 0.2 && item.risk_score < 0.5).length,
    transactions.filter((item) => item.risk_score >= 0.5 && item.risk_score < 0.8).length,
    transactions.filter((item) => item.risk_score >= 0.8).length,
  ], [transactions]);

  if (!currentUser) return <AuthScreen language={language} onAuthenticate={login} />;

  return <div className="app-shell hybrid-dashboard">
    <aside className="sidebar">
      <a className="brand" href="#overview"><span className="brand-mark">◈</span><span className="brand-name">Transfer<span>Guard</span></span></a>
      <div className="workspace-label">{copy.workspace}</div>
      <nav className="side-nav">
        <a className={`nav-link ${route === 'overview' ? 'active' : ''}`} href="#overview" onClick={() => setRoute('overview')}>▦ <span>{copy.overview}</span></a>
        {currentUser.role !== 'compliance' && <button className={`nav-link ${route === 'score' ? 'active' : ''}`} type="button" onClick={() => { setRoute('score'); setAssessmentOpen(true); }}>⌁ <span>{copy.score}</span></button>}
        {currentUser.role !== 'customer' && <a className={`nav-link ${route === 'activity' ? 'active' : ''}`} href="#activity" onClick={() => setRoute('activity')}>☷ <span>{copy.activity}</span></a>}
        {canManageUsers && <button className={`nav-link ${route === 'users' ? 'active' : ''}`} type="button" onClick={() => { setRoute('users'); window.location.hash = '#users'; }}>♙ <span>{copy.users}</span></button>}
      </nav>
      <div className="sidebar-bottom"><div className="environment"><span className="status-dot" />{copy.api}</div><div className="profile-row"><div className="avatar">{currentUser.name.slice(0, 2).toUpperCase()}</div><div className="profile-details"><strong>{currentUser.name}</strong><span>{roleLabel(currentUser.role, language)}</span></div><button type="button" className="logout-button" onClick={logout} title={copy.logout} aria-label={copy.logout}>↪<span>{copy.logout}</span></button></div></div>
    </aside>
    <main className="main-content"><div className="dashboard-toolbar"><span>{copy.language}</span><button className={language === 'en' ? 'active' : ''} onClick={() => setLanguage('en')}>EN</button><button className={language === 'km' ? 'active' : ''} onClick={() => setLanguage('km')}>ខ្មែរ</button><button className="theme-button" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>{theme === 'dark' ? '☀ ' + copy.light : '☾ ' + copy.dark}</button></div>
      {route === 'users' && canManageUsers ? <section className="page-content" id="users"><button className="outline-action" onClick={() => { setRoute('overview'); window.location.hash = '#overview'; }}>{copy.back}</button><h1>User management.</h1><UserManagement currentUser={currentUser} language={language} token={authToken} /></section> : <div className="page-content" id="overview">
        <section className="page-heading"><div><div className="eyebrow">{copy.eyebrow}</div><h1>{copy.title}<span>.</span></h1><p>{copy.subtitle}</p></div>{currentUser.role !== 'compliance' && <button className="outline-action" type="button" onClick={() => setAssessmentOpen(true)}>{copy.newAssessment}</button>}</section>
        <section className="metric-grid hybrid-kpis">
          <article className="metric-card"><div className="metric-top"><span>{copy.evaluated}</span></div><div className="metric-value">{evaluated}</div><div className="metric-foot">Live SQLite activity log</div></article>
          <article className="metric-card"><div className="metric-top"><span>{copy.blocked}</span></div><div className="metric-value">{blocked.length}</div><div className="metric-foot">{ruleBlocked} rules · {mlBlocked} ML</div></article>
          <article className="metric-card"><div className="metric-top"><span>{copy.approval}</span></div><div className="metric-value">{evaluated ? `${Math.round((evaluated - blocked.length) / evaluated * 100)}%` : '--'}</div><div className="metric-foot">Rejected transactions: {blocked.length}</div></article>
          <article className="metric-card"><div className="metric-top"><span>{copy.queue}</span></div><div className="metric-value">{labeled} / 50</div><div className="metric-foot">Verified analyst labels</div></article>
        </section>
        <section className="panel retraining-card" aria-labelledby="retraining-queue-title">
          <div className="retraining-card-header">
            <div>
              <div className="retraining-kicker">ANALYST FEEDBACK &amp; RETRAINING</div>
              <h2 id="retraining-queue-title">Model Retraining Queue</h2>
              <p>Track verified feedback before the next model cycle.</p>
            </div>
            <span className={`retraining-status ${retrainingReady ? 'is-ready' : ''}`}>
              {retrainingReady ? '🟢 Retraining Ready' : '⚪ Collecting Feedback'}
            </span>
          </div>
          <div className="retraining-progress-row">
            <div className="retraining-progress-track" aria-label={`${labeled} of ${retrainingTarget} labels collected`}><span className={retrainingReady ? 'is-ready' : ''} style={{ width: `${retrainingProgress}%` }} /></div>
            <strong>{labeled} / {retrainingTarget} labels ({retrainingProgress}%)</strong>
          </div>
          <div className="retraining-metrics">
            <div><span>Confirmed Fraud</span><strong>{confirmedFraud}</strong><small>Verified as real fraud</small></div>
            <div><span>False Positives</span><strong>{falsePositives}</strong><small>Legitimate transactions</small></div>
            <div><span>Pending Review</span><strong>{pendingReview}</strong><small>Awaiting analyst inspection</small></div>
          </div>
          {labeled === 0 && <p className="retraining-empty">No feedback recorded yet. Score a transaction above and mark it in the Activity Log.</p>}
          {retrainingNotice && <p className="retraining-notice" role="status">{retrainingNotice}</p>}
          <div className="retraining-actions">
            <button className="retraining-trigger" type="button" disabled={!retrainingReady && !canManageUsers} onClick={() => setRetrainingNotice(retrainingReady ? 'Retraining cycle queued for the next model run.' : 'Manual retraining override queued by an administrator.')}>Trigger Retraining Now</button>
            {!retrainingReady && !canManageUsers && <span>Available when 50 verified labels are collected.</span>}
            {!retrainingReady && canManageUsers && <span>Administrator override enabled.</span>}
          </div>
        </section>
        <section className="visual-grid">
          <article className="panel analytics-panel"><div className="panel-heading"><div><h2>Rule vs. ML distribution</h2><p>Rejection source across logged assessments</p></div></div><div className="split-bars"><div><strong>Stage 1 · Rules</strong><span>{ruleBlocked}</span><i style={{ width: `${blocked.length ? ruleBlocked / blocked.length * 100 : 0}%` }} /></div><div><strong>Stage 2 · CatBoost</strong><span>{mlBlocked}</span><i className="ml-bar" style={{ width: `${blocked.length ? mlBlocked / blocked.length * 100 : 0}%` }} /></div></div></article>
          <article className="panel analytics-panel"><div className="panel-heading"><div><h2>Risk score histogram</h2><p>Current local transaction sample</p></div></div><div className="histogram">{buckets.map((count, index) => <div className="histogram-column" key={index}><span>{count}</span><i style={{ height: `${Math.max(4, count / Math.max(1, ...buckets) * 100)}%` }} /><small>{['0–20%', '20–50%', '50–80%', '80–100%'][index]}</small></div>)}</div></article>
        </section>
        
        {currentUser.role !== 'customer' && (<section className="panel activity-panel" id="activity"><div className="panel-heading activity-heading"><div><h2>{copy.activityTitle}</h2><p>{copy.activitySub}</p></div><span className="record-count">{labeled} / 50 labels</span></div>{transactions.length ? <div className="table-scroll"><table><thead><tr><th>ID / Time</th><th>Tier</th><th>Risk</th><th>SHAP / reasons</th><th>Analyst action</th></tr></thead><tbody>{transactions.map((item) => <tr key={item.id}><td>#{item.id}<span className="transaction-sub">{item.timestamp ? new Date(item.timestamp).toLocaleString() : '—'}</span></td><td>{item.decision === 'FLAGGED_BY_RULES' ? 'Stage 1 · Rules' : 'Stage 2 · ML'}</td><td><strong>{(item.risk_score * 100).toFixed(1)}%</strong></td><td>{item.reasons?.[0] ?? '—'}</td><td>{item.confirmed_label === null || item.confirmed_label === undefined ? <><button className="feedback-button fraud-feedback" onClick={() => void submitFeedback(item.id!, 1)}>{copy.confirm}</button><button className="feedback-button" onClick={() => void submitFeedback(item.id!, 0)}>{copy.falsePositive}</button></> : <span className="label-chip">Labeled: {item.confirmed_label === 1 ? 'Fraud' : 'Legitimate'}</span>}</td></tr>)}</tbody></table></div> : <div className="empty-table">No API transactions yet. Score a transaction above after starting app.py.</div>}</section>)}
        <footer className="page-footer"><span>TransferGuard · Credit-card fraud research</span><span>Two-tier hybrid API · SQLite feedback loop</span></footer>
      </div>}
      {assessmentOpen && <div className="assessment-modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.currentTarget === event.target) setAssessmentOpen(false); }}><div className="assessment-modal" role="dialog" aria-modal="true" aria-labelledby="assessment-modal-title"><div className="assessment-modal-heading"><div><div className="modal-kicker">TWO-TIER FRAUD ASSESSMENT</div><h2 id="assessment-modal-title">{copy.scoreTitle}</h2><p>{copy.scoreSub}</p></div><button className="modal-close-button" type="button" aria-label="Close" onClick={() => setAssessmentOpen(false)}>×</button></div><form onSubmit={scoreTransaction}><label>{copy.amount}<input autoFocus type="number" min="0" step="0.01" value={amount} onChange={(event) => setAmount(+event.target.value)} /></label><label>{copy.time}<input type="number" min="0" value={time} onChange={(event) => setTime(+event.target.value)} /></label><label className="checkbox-label"><input type="checkbox" checked={blacklisted} onChange={(event) => setBlacklisted(event.target.checked)} /> {copy.blacklisted}</label>{error && <div className="error-message">{error}</div>}<div className="modal-actions"><button className="modal-cancel-button" type="button" onClick={() => setAssessmentOpen(false)}>Cancel</button><button className="submit-button" type="submit" disabled={loading}>{loading ? copy.analyzing : copy.analyze}</button></div></form></div></div>}    </main>
  </div>;
}

createRoot(document.getElementById('root')!).render(<App />);
