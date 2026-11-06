import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { authenticateDemo, AuthScreen, UserManagement, type SessionUser } from './auth';
import { getMessages, type Language } from './i18n';
import './style.css';

type Result = {
	transaction_id: string | null;
	risk_score: number;
	threshold: number;
	alert: boolean;
	model: string;
};

type NavigationKey = 'overview' | 'scoreTransfer' | 'activityLog' | 'userManagement';

const navigation: { key: NavigationKey; icon: string; target: string }[] = [
	{ key: 'overview', icon: 'grid', target: '#overview' },
	{ key: 'scoreTransfer', icon: 'scan', target: '#score-transfer' },
	{ key: 'activityLog', icon: 'list', target: '#activity' },
];

const demoResults: Result[] = [
	{ transaction_id: 'DEMO-1048', risk_score: 0.91, threshold: 0.70, alert: true, model: 'Demo simulation' },
	{ transaction_id: 'DEMO-1047', risk_score: 0.18, threshold: 0.70, alert: false, model: 'Demo simulation' },
	{ transaction_id: 'DEMO-1046', risk_score: 0.64, threshold: 0.70, alert: false, model: 'Demo simulation' },
	{ transaction_id: 'DEMO-1045', risk_score: 0.82, threshold: 0.70, alert: true, model: 'Demo simulation' },
	{ transaction_id: 'DEMO-1044', risk_score: 0.33, threshold: 0.70, alert: false, model: 'Demo simulation' },
];

function Icon({ name }: { name: string }) {
	const paths: Record<string, React.ReactNode> = {
		grid: <><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></>,
		scan: <><path d="M4 8V5a1 1 0 0 1 1-1h3M16 4h3a1 1 0 0 1 1 1v3M20 16v3a1 1 0 0 1-1 1h-3M8 20H5a1 1 0 0 1-1-1v-3" /><path d="M7 12h10M12 7v10" /></>,
		list: <><path d="M9 6h11M9 12h11M9 18h11" /><path d="M4 6h.01M4 12h.01M4 18h.01" /></>,
		arrow: <><path d="M7 17 17 7M7 7h10v10" /></>,
		shield: <><path d="M12 22s8-4 8-11V5l-8-3-8 3v6c0 7 8 11 8 11Z" /><path d="m9 12 2 2 4-4" /></>,
		clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
		bolt: <path d="m13 2-3 8h7l-6 12 2-9H6l7-11Z" />,
		users: <><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M20 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" /></>,
		logout: <><path d="M10 17l5-5-5-5M15 12H3" /><path d="M12 3h6a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-6" /></>,
		transfer: <><path d="M4 8h14l-3-3M18 8l-3 3M20 16H6l3 3M6 16l3-3" /></>,
		flag: <><path d="M5 3v18" /><path d="M5 4h12l-2.5 4L17 12H5" /></>,
		moon: <path d="M20.5 14.5A8.5 8.5 0 0 1 9.5 3.5a8.6 8.6 0 1 0 11 11Z" />,
		sun: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.93 4.93l1.42 1.42m11.3 11.3 1.42 1.42M2 12h2m16 0h2M4.93 19.07l1.42-1.42m11.3-11.3 1.42-1.42" /></>,
	};

	return <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">{paths[name]}</svg>;
}

function App() {
	const [currentRoute, setCurrentRoute] = useState<'dashboard' | 'users'>(() => window.location.pathname === '/users' ? 'users' : 'dashboard');
	const [amount, setAmount] = useState(2000);
	const [balance, setBalance] = useState(5000);
	const [step, setStep] = useState(1);
	const [type, setType] = useState('TRANSFER');
	const [items, setItems] = useState<Result[]>(demoResults);
	const [error, setError] = useState('');
	const [currentUser, setCurrentUser] = useState<SessionUser | null>(null);
	const [language, setLanguage] = useState<Language>(() => localStorage.getItem('transferguard-language') === 'km' ? 'km' : 'en');
	const t = getMessages(language);
	const [theme, setTheme] = useState<'light' | 'dark'>(() => (localStorage.getItem('transferguard-theme') ?? localStorage.getItem('transferlab-theme')) === 'dark' ? 'dark' : 'light');

	useEffect(() => {
		document.documentElement.dataset.theme = theme;
		localStorage.setItem('transferguard-theme', theme);
	}, [theme]);

	useEffect(() => {
		document.documentElement.lang = language;
		localStorage.setItem('transferguard-language', language);
	}, [language]);

	useEffect(() => {
		function restoreRoute() {
			setCurrentRoute(window.location.pathname === '/users' ? 'users' : 'dashboard');
		}
		window.addEventListener('popstate', restoreRoute);
		return () => window.removeEventListener('popstate', restoreRoute);
	}, []);

	const alertCount = items.filter((item) => item.alert).length;
	const averageRisk = items.length
		? items.reduce((total, item) => total + item.risk_score, 0) / items.length
		: null;
	const latestThreshold = items[0]?.threshold;
	const visibleNavigation = currentUser?.role === 'admin'
		? [...navigation, { key: 'userManagement', icon: 'users', target: '/users' }]
		: navigation;

	function navigateTo(route: 'dashboard' | 'users') {
		const path = route === 'users' ? '/users' : '/';
		if (window.location.pathname !== path) window.history.pushState({}, '', path);
		setCurrentRoute(route);
		window.scrollTo({ top: 0, behavior: 'smooth' });
	}

	function authenticate(email: string, password: string) {
		setCurrentUser(authenticateDemo(email, password, t.useDemoPassword));
	}

	function logout() {
		setCurrentUser(null);
		setItems(demoResults);
		setError('');
		navigateTo('dashboard');
	}

	function predict(event: React.FormEvent<HTMLFormElement>) {
		event.preventDefault();
		setError('');
	const riskScore = Math.min(0.98, Math.max(0.03,
		0.10 + Math.log1p(amount) / 30 + Math.log1p(balance) / 80 + (type === 'CASH_OUT' ? 0.16 : 0) + (step > 300 ? 0.05 : 0)));
	setItems((current) => [{
		transaction_id: `DEMO-${Date.now().toString().slice(-6)}`,
		risk_score: riskScore,
		threshold: 0.70,
		alert: riskScore >= 0.70,
		model: 'Demo simulation',
	}, ...current].slice(0, 30));
	}

	if (!currentUser) {
		return <AuthScreen language={language} onAuthenticate={authenticate} />;
	}

	return (
		<div className="app-shell" id="overview">
			<aside className="sidebar">
				<a className="brand" href="#overview" aria-label="TransferGuard home">
					<span className="brand-mark"><Icon name="transfer" /></span>
					<span className="brand-name">Transfer<span>Guard</span></span>
				</a>

				<div className="workspace-label">WORKSPACE</div>
				<nav className="side-nav" aria-label="Main navigation">
					{visibleNavigation.map((item, index) => (
						<a className={`nav-link ${item.target === '/users' ? currentRoute === 'users' ? 'active' : '' : index === 0 && currentRoute === 'dashboard' ? 'active' : ''}`} href={item.target} key={item.key} onClick={(event) => {
							if (item.target === '/users') {
								event.preventDefault();
								navigateTo('users');
							}
						}}>
							<Icon name={item.icon} />
							<span>{t[item.key]}</span>
							{item.key === 'activityLog' && <span className="nav-count">{items.length}</span>}
						</a>
					))}
				</nav>

				<div className="sidebar-bottom">
					<div className="environment"><span className="status-dot" />Local research environment</div>
					<div className="profile-row">
						<div className="avatar">{currentUser.name.split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase()}</div>
						<div><strong>{currentUser.name}</strong><span>{currentUser.role === 'admin' ? t.administrator : t.researcher}</span></div>
						<button className="logout-button" type="button" title="Sign out" aria-label="Sign out" onClick={() => void logout()}><Icon name="logout" /></button>
					</div>
				</div>
			</aside>

			<main className="main-content">
				<header className="topbar">
					  <div className="breadcrumb"><a href="/" onClick={(event) => { event.preventDefault(); navigateTo('dashboard'); }}>TransferGuard</a><span>/</span><strong>{currentRoute === 'users' && currentUser.role === 'admin' ? t.userManagement : t.researchOverview}</strong></div>
					  <div className="topbar-right"><span className="account-role">{currentUser.role === 'admin' ? t.admin : t.researcherCaps}</span><span className="workspace-mode">{t.demoMode}</span><span className="date-label">{t.localExperiment}</span><div className="language-switch" role="group" aria-label="Language"><button className={language === 'en' ? 'active' : ''} type="button" aria-pressed={language === 'en'} onClick={() => setLanguage('en')}>EN</button><span aria-hidden="true">|</span><button className={language === 'km' ? 'active' : ''} type="button" aria-pressed={language === 'km'} onClick={() => setLanguage('km')}>ខ្មែរ</button></div><button className="theme-toggle" type="button" title={theme === 'dark' ? 'Light mode' : 'Dark mode'} aria-label={theme === 'dark' ? 'Light mode' : 'Dark mode'} aria-pressed={theme === 'dark'} onClick={() => setTheme((current) => current === 'dark' ? 'light' : 'dark')}><Icon name={theme === 'dark' ? 'sun' : 'moon'} /></button><button className="logout-button topbar-logout" type="button" title="Sign out" aria-label="Sign out" onClick={logout}><Icon name="logout" /></button></div>
				</header>

				<div className={`page-content ${currentRoute === 'users' && currentUser.role === 'admin' ? 'route-hidden' : ''}`}>
					<section className="page-heading">
						<div>
							  <div className="eyebrow">{t.moneyTransferResearch}</div>
							  <h1>{t.researchOverview}<span>.</span></h1>
							  <p>{t.overviewDescription}</p>
						</div>
						<a className="outline-action" href="#score-transfer"><Icon name="bolt" /> {t.newAssessment}</a>
					</section>

					<section className="metric-grid" aria-label={t.scoringSummary}>
						<article className="metric-card metric-primary">
							<div className="metric-top"><span>{t.paysimRecords}</span><span className="metric-icon"><Icon name="list" /></span></div>
							<div className="metric-value">6.36M</div>
							<div className="metric-foot">{t.fullSyntheticDataset}</div>
						</article>
						<article className="metric-card">
							<div className="metric-top"><span>{t.observedFraudRate}</span><span className="metric-icon alert-icon"><Icon name="arrow" /></span></div>
							<div className="metric-value">0.129%</div>
							<div className="metric-foot">{t.fraudCases}</div>
						</article>
						<article className="metric-card">
							<div className="metric-top"><span>{t.modelCandidates}</span><span className="metric-icon"><Icon name="bolt" /></span></div>
							<div className="metric-value">03</div>
							<div className="metric-foot">{t.modelCandidateNames}</div>
						</article>
						<article className="metric-card">
							<div className="metric-top"><span>{t.thresholdSelection}</span><span className="metric-icon"><Icon name="shield" /></span></div>
							<div className="metric-value metric-word">{t.validationF1}</div>
							<div className="metric-foot">{t.validationNote}</div>
						</article>
					</section>

					<section className="research-strip" aria-label="Research scope and baseline features">
						<div className="research-strip-heading"><span>{t.experimentDesign}</span><strong>{t.leakageAware}</strong></div>
						<p>{t.experimentDescription}</p>
						<div className="feature-tags" aria-label={t.baselineInputs}>
							<span>amount</span><span>step</span><span>type_TRANSFER</span><span>type_CASH_OUT</span><span>oldbalanceOrg</span>
						</div>
						<div className="research-caveat"><Icon name="shield" /><span>{t.syntheticCaveat}</span></div>
					</section>

					<section className="visual-grid">
						<article className="panel risk-panel">
							<div className="panel-heading">
								<div><h2>{t.sessionRiskScores}</h2><p>{t.illustrativeOnly}</p></div>
										<span className="period-label"><Icon name="clock" /> {t.demoData}</span>
							</div>
							{items.length ? (
								<div className="chart-wrap" role="img" aria-label={t.sessionRiskScores}>
									<div className="chart-y-labels"><span>100%</span><span>75%</span><span>50%</span><span>25%</span><span>0%</span></div>
									<div className="bar-chart">
										{[...items].reverse().map((item, index) => (
											<div className="bar-column" key={`${item.transaction_id}-${index}`} title={`Transaction ${item.transaction_id ?? 'unknown'}: ${(item.risk_score * 100).toFixed(1)}%`}>
												<div className={`bar ${item.alert ? 'bar-alert' : ''}`} style={{ height: `${Math.max(3, Math.min(100, item.risk_score * 100))}%` }} />
												<span>{index % Math.max(1, Math.ceil(items.length / 6)) === 0 ? `#${index + 1}` : ''}</span>
											</div>
										))}
									</div>
									<div className="chart-gridlines"><i /><i /><i /><i /><i /></div>
								</div>
							) : (
								<div className="empty-chart"><div className="empty-chart-mark"><Icon name="bolt" /></div><strong>{t.noScoredTransfers}</strong><span>{t.scoresAppear}</span></div>
							)}
							  <div className="chart-legend"><span><i className="legend-blue" />{t.noAlert}</span><span><i className="legend-orange" />{t.reviewAlert}</span><span className="chart-source">{t.currentSession}</span></div>
						</article>

						<article className="panel alert-panel">
							<div className="panel-heading"><div><h2>{t.sessionProfile}</h2><p>{t.alertShare}</p></div><span className="more-mark">•••</span></div>
							<div className="donut-area">
								<div className="donut" style={{ '--alert-share': `${items.length ? (alertCount / items.length) * 100 : 0}%` } as React.CSSProperties}>
									<div><strong>{items.length ? `${Math.round((alertCount / items.length) * 100)}%` : '--'}</strong><span>{t.alerts}</span></div>
								</div>
								<div className="donut-caption"><span><i className="legend-orange" />{t.reviewAlert}</span><strong>{alertCount}</strong><span><i className="legend-blue" />{t.noAlert}</span><strong>{items.length - alertCount}</strong></div>
							</div>
							<div className="session-details"><span>{t.meanSessionRisk}<strong>{averageRisk === null ? '--' : `${(averageRisk * 100).toFixed(1)}%`}</strong></span><span>{t.modelThreshold}<strong>{latestThreshold === undefined ? '--' : `${(latestThreshold * 100).toFixed(1)}%`}</strong></span></div>
							<div className="threshold-note"><Icon name="shield" /><span>{t.alertCaveat}</span></div>
						</article>
					</section>

					<section className="lower-grid">
						<article className="panel activity-panel" id="activity">
							<div className="panel-heading activity-heading"><div><h2>{t.recentAssessments}</h2><p>{t.latestScored}</p></div><span className="record-count">{items.length} {t.records}</span></div>
							{items.length ? (
								<div className="table-scroll"><table>
									<thead><tr><th>{t.transaction}</th><th>{t.model}</th><th>{t.riskScore}</th><th>{t.assessment}</th></tr></thead>
									<tbody>{items.map((item, index) => (
										<tr key={`${item.transaction_id}-${index}`}>
											<td><span className="transaction-id">{item.transaction_id ?? t.idUnavailable}</span><span className="transaction-sub">{t.moneyTransfer}</span></td>
											<td><span className="model-tag">{item.model}</span></td>
											<td><strong className="score-number">{(item.risk_score * 100).toFixed(2)}%</strong><span className="score-track"><i style={{ width: `${Math.min(100, Math.max(0, item.risk_score * 100))}%` }} /></span></td>
											<td><span className={`result-status ${item.alert ? 'status-alert' : 'status-clear'}`}><i />{item.alert ? t.reviewAlert : t.noAlert}</span></td>
										</tr>
									))}</tbody>
								</table></div>
							) : <div className="empty-table">{t.noAssessments}</div>}
						</article>

						<article className="panel form-panel" id="score-transfer">
							<div className="panel-heading"><div><h2>{t.sampleTransfer}</h2><p>{t.demoScoringInteraction}</p></div><span className="form-mark"><Icon name="scan" /></span></div>
							<form onSubmit={predict}>
								<label>{t.transactionAmount} <span className="input-wrap"><input type="number" min="0" step="0.01" value={amount} onChange={(event) => setAmount(+event.target.value)} required /></span></label>
								<label>{t.originBalance} <span className="input-wrap"><input type="number" min="0" step="0.01" value={balance} onChange={(event) => setBalance(+event.target.value)} required /></span></label>
								<div className="form-row">
									<label>{t.timeStep}<input type="number" min="0" value={step} onChange={(event) => setStep(+event.target.value)} required /></label>
									<label>{t.transferType}<select value={type} onChange={(event) => setType(event.target.value)}><option value="TRANSFER">{t.transfer}</option><option value="CASH_OUT">{t.cashOut}</option></select></label>
								</div>
								{error && <div className="error-message" role="alert">{error}</div>}
								<button className="submit-button" type="submit"><Icon name="scan" />{t.runDemoAssessment}<Icon name="arrow" /></button>
								<p className="form-disclaimer">{t.illustrativeScoreNote}</p>
							</form>
						</article>
					</section>
					<footer className="page-footer"><span>TransferGuard <b>·</b> {t.footerResearch}</span><span>{t.demoSimulationNoApi}</span></footer>
				</div>
				{currentUser.role === 'admin' && <div className={`page-content users-page ${currentRoute === 'users' ? '' : 'route-hidden'}`}>
					<section className="page-heading">
						<div>
							<div className="eyebrow">{t.workspaceAccess}</div>
							<h1>{t.userManagement}<span>.</span></h1>
							<p>{t.manageRoles}</p>
						</div>
						<button className="outline-action" type="button" onClick={() => navigateTo('dashboard')}><Icon name="grid" /> {t.backOverview}</button>
					</section>
					<UserManagement currentUser={currentUser} language={language} />
					<footer className="page-footer"><span>TransferGuard <b>·</b> {t.demoUserDirectory}</span><span>{t.memoryReset}</span></footer>
				</div>}
			</main>
		</div>
	);
}

createRoot(document.getElementById('root')!).render(<App />);
