import React, { useState } from 'react';
import { getMessages, type Language } from './i18n';

export type SessionUser = {
  id: number;
  name: string;
  email: string;
  role: 'admin' | 'researcher';
  active: boolean;
  created_at: number;
};

export const DEMO_PASSWORD = 'transfer-demo-2026';
export const DEMO_USERS: SessionUser[] = [
  { id: 1, name: 'Research Admin', email: 'admin@transferguard.demo', role: 'admin', active: true, created_at: 1761696000 },
  { id: 2, name: 'Fraud Analyst', email: 'analyst@transferguard.demo', role: 'researcher', active: true, created_at: 1761782400 },
];

export function authenticateDemo(email: string, password: string, invalidMessage: string): SessionUser {
  const user = DEMO_USERS.find((account) => account.email === email.trim().toLowerCase() && account.active);
  if (!user || password !== DEMO_PASSWORD) throw new Error(invalidMessage);
  return { ...user };
}

type AuthScreenProps = {
  language: Language;
  onAuthenticate: (email: string, password: string) => void;
};

export function AuthScreen({ language, onAuthenticate }: AuthScreenProps) {
  const t = getMessages(language);
  const [email, setEmail] = useState(DEMO_USERS[0].email);
  const [password, setPassword] = useState(DEMO_PASSWORD);
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    setIsSubmitting(true);
    try {
      onAuthenticate(email, password);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="auth-shell">
      <section className="auth-story">
        <a className="brand auth-brand" href="#login" aria-label="TransferGuard">
          <span className="brand-mark"><svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M4 8h14l-3-3M18 8l-3 3M20 16H6l3 3M6 16l3-3" /></svg></span>
          <span className="brand-name">Transfer<span>Guard</span></span>
        </a>
        <div className="auth-story-copy">
          <span className="auth-kicker">MONEY TRANSFER · RESEARCH WORKSPACE</span>
          <h1>Study the signal.<br /><span>Question the score.</span></h1>
          <p>A private workspace for exploring synthetic PaySim fraud patterns and evaluating a leakage-aware baseline.</p>
        </div>
        <div className="auth-story-footer"><span className="story-dot" />LOCAL RESEARCH ENVIRONMENT<span className="story-divider" />PAYSIM DATASET</div>
      </section>

      <section className="auth-panel" id="login">
        <div className="auth-panel-inner">
          <span className="auth-step">{t.demoWorkspace}</span>
          <h2>{t.welcomeLab}</h2>
          <p className="auth-subtitle">{t.loginDescriptionShort}</p>
          <form className="auth-form" onSubmit={submit}>
            <label>{t.demoAccount}<input type="email" autoComplete="username" value={email} onChange={(event) => setEmail(event.target.value)} required maxLength={254} /></label>
            <label>{t.samplePassword}<input type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required maxLength={200} /></label>
            {error && <div className="auth-error" role="alert">{error}</div>}
            <button type="submit" disabled={isSubmitting}>{isSubmitting ? t.openingWorkspace : t.enterDemo}<span aria-hidden="true">↗</span></button>
          </form>
          <div className="demo-account-choices">
            <button type="button" onClick={() => { setEmail(DEMO_USERS[0].email); setPassword(DEMO_PASSWORD); }}>{t.adminDemo}<span>admin@transferguard.demo</span></button>
            <button type="button" onClick={() => { setEmail(DEMO_USERS[1].email); setPassword(DEMO_PASSWORD); }}>{t.researcherDemo}<span>analyst@transferguard.demo</span></button>
          </div>
          <div className="demo-password">{t.samplePassword} <code>{DEMO_PASSWORD}</code></div>
          <div className="auth-security-note"><svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"><rect x="4" y="10" width="16" height="11" rx="2" /><path d="M8 10V7a4 4 0 0 1 8 0v3M12 14v3" /></svg><span>{t.demoOnlyNotice}</span></div>
        </div>
        <footer className="auth-footer">TransferGuard <span>·</span> {t.researchPrototype}</footer>
      </section>
    </main>
  );
}

type UserManagementProps = {
  currentUser: SessionUser;
};

export function UserManagement({ currentUser, language }: UserManagementProps & { language: Language }) {
  const t = getMessages(language);
  const [users, setUsers] = useState<SessionUser[]>(() => DEMO_USERS.map((user) => ({ ...user })));
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<SessionUser['role']>('researcher');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [pendingDeleteId, setPendingDeleteId] = useState<number | null>(null);
  const [editingUserId, setEditingUserId] = useState<number | null>(null);
  const [editName, setEditName] = useState('');
  const [editEmail, setEditEmail] = useState('');

  function createAccount(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    setNotice('');
    try {
      if (password.length < 12) throw new Error(t.passwordTooShort);
      if (users.some((user) => user.email === email.trim().toLowerCase())) throw new Error(t.duplicateEmail);
      const created: SessionUser = {
        id: Math.max(...users.map((user) => user.id), 0) + 1,
        name: name.trim(),
        email: email.trim().toLowerCase(),
        role,
        active: true,
        created_at: Math.floor(Date.now() / 1000),
      };
      setUsers((current) => [...current, created]);
      setName('');
      setEmail('');
      setPassword('');
      setRole('researcher');
      setNotice(`${t.accountCreated} ${created.name}.`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    }
  }

  function updateAccount(userId: number, patch: { role?: SessionUser['role']; active?: boolean }) {
    setError('');
    setNotice('');
    try {
      const target = users.find((user) => user.id === userId);
      if (!target) throw new Error(t.accountNotFound);
      const nextRole = patch.role ?? target.role;
      const nextActive = patch.active ?? target.active;
      if (userId === currentUser.id && !nextActive) throw new Error(t.noSelfDeactivate);
      if (target.role === 'admin' && target.active && (nextRole !== 'admin' || !nextActive)
        && users.filter((user) => user.role === 'admin' && user.active).length <= 1) {
        throw new Error(t.lastAdmin);
      }
      const updated = { ...target, ...patch };
      setUsers((current) => current.map((user) => user.id === userId ? updated : user));
      setNotice(`${t.accountUpdated} ${updated.name}.`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    }
  }

  function beginEdit(user: SessionUser) {
    setEditingUserId(user.id);
    setEditName(user.name);
    setEditEmail(user.email);
    setError('');
    setNotice('');
  }

  function cancelEdit() {
    setEditingUserId(null);
    setEditName('');
    setEditEmail('');
  }

  function saveEdit(userId: number) {
    const nextName = editName.trim();
    const nextEmail = editEmail.trim().toLowerCase();
    if (!nextName || !nextEmail) {
      setError('Full name and email address are required.');
      return;
    }
    if (users.some((user) => user.id !== userId && user.email === nextEmail)) {
      setError(t.duplicateEmail);
      return;
    }
    const updated = users.find((user) => user.id === userId);
    if (!updated) {
      setError(t.accountNotFound);
      return;
    }
    setUsers((current) => current.map((user) => user.id === userId ? { ...user, name: nextName, email: nextEmail } : user));
    setEditingUserId(null);
    setEditName('');
    setEditEmail('');
    setNotice(`${t.accountUpdated} ${nextName}.`);
    setError('');
  }

  function deleteAccount(userId: number) {
    setError('');
    setNotice('');
    const target = users.find((user) => user.id === userId);
    if (!target) return;
    if (userId === currentUser.id) {
      setError(t.noSelfDelete);
      return;
    }
    if (target.role === 'admin' && target.active
      && users.filter((user) => user.role === 'admin' && user.active).length <= 1) {
      setError(t.lastAdmin);
      return;
    }
    setUsers((current) => current.filter((user) => user.id !== userId));
    setPendingDeleteId(null);
    setNotice(`${t.accountDeleted} ${target.name}.`);
  }

  const editingUser = users.find((user) => user.id === editingUserId);

  return (
    <section className="panel user-management" id="user-management">
      <div className="panel-heading user-management-heading">
        <div><h2>{t.userManagement}</h2><p>{t.workspaceAccounts}</p></div>
        <span className="record-count">{t.administrator}</span>
      </div>
      <div className="user-management-grid">
        <form className="user-create-form" onSubmit={createAccount}>
          <div className="user-form-heading"><strong>{t.addDemoAccount}</strong><span>{t.sampleAccountsHelp}</span></div>
          <label><span>{t.fullName}<span className="required-mark" aria-hidden="true"> *</span></span><input value={name} onChange={(event) => setName(event.target.value)} required maxLength={100} /></label>
          <label><span>{t.emailAddress}<span className="required-mark" aria-hidden="true"> *</span></span><input type="email" autoComplete="off" value={email} onChange={(event) => setEmail(event.target.value)} required maxLength={254} /></label>
          <div className="user-form-row">
            <label><span>{t.temporaryPassword}<span className="required-mark" aria-hidden="true"> *</span></span><input type="password" autoComplete="new-password" value={password} onChange={(event) => setPassword(event.target.value)} required minLength={12} maxLength={200} /></label>
            <label>{t.role}<select value={role} onChange={(event) => setRole(event.target.value as SessionUser['role'])}><option value="researcher">{t.researcher}</option><option value="admin">{t.administrator}</option></select></label>
          </div>
          <small className="password-help">{t.minimumPassword}</small>
          <button type="submit" className="user-add-button">{t.createAccount}<span aria-hidden="true">+</span></button>
        </form>

        <div className="user-directory">
          <div className="user-directory-heading"><div className="directory-title"><strong>{t.workspaceDirectory}</strong><span className="directory-edit-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20h9" /><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L8 18l-4 1 1-4Z" /></svg></span></div><span>{users.length} {t.account}</span></div>
          {error && <div className="user-feedback user-feedback-error" role="alert">{error}</div>}
          {notice && <div className="user-feedback" role="status">{notice}</div>}
          {users.length === 0 ? <div className="user-empty">{t.noDemoAccounts}</div> : (
            <div className="user-list">
              {users.map((user) => (
                <article className="user-row" key={user.id}>
                  <div className="user-avatar">{user.name.split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase()}</div>
                  <div className="user-identity"><strong>{user.name}{user.id === currentUser.id ? <span className="you-tag">{t.you}</span> : null}</strong><span>{user.email}</span></div>
                  <div className="user-row-tools">
                    <select aria-label={`${t.role} ${user.name}`} value={user.role} disabled={user.id === currentUser.id} onChange={(event) => updateAccount(user.id, { role: event.target.value as SessionUser['role'] })}>
                      <option value="researcher">{t.researcher}</option><option value="admin">{t.administrator}</option>
                    </select>
                    <button type="button" className={`user-state-button ${user.active ? '' : 'is-inactive'}`} disabled={user.id === currentUser.id} onClick={() => updateAccount(user.id, { active: !user.active })}>
                      <i />{user.id === currentUser.id ? t.current : user.active ? t.active : t.inactive}
                    </button>
                    {pendingDeleteId === user.id ? (
                      <span className="delete-confirmation"><span>{t.deleteQuestion}</span><button type="button" onClick={() => deleteAccount(user.id)}>{t.confirm}</button><button type="button" onClick={() => setPendingDeleteId(null)}>{t.cancel}</button></span>
                    ) : (
                      <>
                        <button type="button" className="user-edit-button" title={`${t.edit} ${user.name}`} aria-label={`${t.edit} ${user.name}`} onClick={() => beginEdit(user)}><svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20h9" /><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L8 18l-4 1 1-4Z" /></svg></button>
                        <button type="button" className="user-delete-button" title={`${t.delete} ${user.name}`} aria-label={`${t.delete} ${user.name}`} disabled={user.id === currentUser.id} onClick={() => setPendingDeleteId(user.id)}>
                          <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M3 6h18M8 6V4h8v2m3 0-1 14H6L5 6m4 4v6m6-6v6" /></svg>
                        </button>
                      </>
                    )}
                  </div>
                </article>
              ))}
            </div>
          )}
        </div>
      </div>
      {editingUser && (<div className="user-edit-modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.currentTarget === event.target) cancelEdit(); }}><div className="user-edit-modal" role="dialog" aria-modal="true" aria-labelledby="edit-user-title"><div className="user-edit-modal-heading"><strong id="edit-user-title">{t.edit} {editingUser.name}</strong><button type="button" className="modal-close-button" aria-label={t.cancel} onClick={cancelEdit}>×</button></div><label><span>{t.fullName}<span className="required-mark" aria-hidden="true"> *</span></span><input value={editName} onChange={(event) => setEditName(event.target.value)} required autoFocus /></label><label><span>{t.emailAddress}<span className="required-mark" aria-hidden="true"> *</span></span><input type="email" value={editEmail} onChange={(event) => setEditEmail(event.target.value)} required /></label><div className="user-edit-modal-actions"><button type="button" className="modal-cancel-button" onClick={cancelEdit}>{t.cancel}</button><button type="button" className="modal-update-button" onClick={() => saveEdit(editingUser.id)}>{t.update}</button></div></div></div>)}
      <div className="role-access">
        <div className="user-directory-heading"><strong>{t.roleAccess}</strong><span>{t.demoPermissions}</span></div>
        <div className="role-access-scroll"><table className="role-access-table">
          <thead><tr><th>{t.role.toUpperCase()}</th><th>{t.researchOverviewAccess}</th><th>{t.demoAssessments}</th><th>{t.userManagement}</th></tr></thead>
          <tbody>
            <tr><td><strong>{t.administrator}</strong></td><td>{t.allowed}</td><td>{t.allowed}</td><td>{t.allowed}</td></tr>
            <tr><td><strong>{t.researcher}</strong></td><td>{t.allowed}</td><td>{t.allowed}</td><td>{t.notAllowed}</td></tr>
          </tbody>
        </table></div>
      </div>
      <p className="user-management-footnote">{t.demoDataReset}</p>
    </section>
  );
}