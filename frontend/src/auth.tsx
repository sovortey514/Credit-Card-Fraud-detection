import React, { useEffect, useMemo, useState } from 'react';
import { getMessages, type Language } from './i18n';

export type SessionUser = {
  id: number;
  name: string;
  email: string;
  role: 'admin' | 'analyst' | 'customer' | 'compliance';
  active: boolean;
  created_at: number;
};

export const DEMO_PASSWORD = 'transfer-demo-2026';
export const DEMO_USERS: SessionUser[] = [
  { id: 1, name: 'Risk Manager', email: 'admin@transferguard.demo', role: 'admin', active: true, created_at: 1761696000 },
  { id: 2, name: 'Fraud Analyst', email: 'analyst@transferguard.demo', role: 'analyst', active: true, created_at: 1761782400 },

  { id: 3, name: 'Cardholder Demo', email: 'customer@transferguard.demo', role: 'customer', active: true, created_at: 1761868800 },
  { id: 4, name: 'Compliance Officer', email: 'compliance@transferguard.demo', role: 'compliance', active: true, created_at: 1761955200 },];
export function roleLabel(role: SessionUser['role'], language: Language): string {
  if (language === 'km') return ({ admin: 'អ្នកគ្រប់គ្រងហានិភ័យ', analyst: 'អ្នកវិភាគក្លែងបន្លំ', customer: 'អតិថិជន', compliance: 'មន្ត្រីអនុលោមភាព' })[role];
  return ({ admin: 'Risk Manager / Admin', analyst: 'Fraud Analyst', customer: 'Cardholder / Customer', compliance: 'Compliance Officer' })[role];
}

export function authenticateDemo(email: string, password: string, invalidMessage: string): SessionUser {
  const user = DEMO_USERS.find((account) => account.email === email.trim().toLowerCase() && account.active);
  if (!user || password !== DEMO_PASSWORD) throw new Error(invalidMessage);
  return { ...user };
}

type AuthScreenProps = {
  language: Language;
  onAuthenticate: (email: string, password: string) => Promise<void>;
};

export function AuthScreen({ language, onAuthenticate }: AuthScreenProps) {
  const t = getMessages(language);
  const [email, setEmail] = useState(DEMO_USERS[0].email);
  const [password, setPassword] = useState(DEMO_PASSWORD);
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [resetOpen, setResetOpen] = useState(false);
  const [resetToken, setResetToken] = useState('');
  const [resetPassword, setResetPassword] = useState('');
  const [resetNotice, setResetNotice] = useState('');

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    setIsSubmitting(true);
    try {
      await onAuthenticate(email, password);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function requestReset() {
    setError(''); setResetNotice('');
    const response = await fetch('http://localhost:5000/api/v1/auth/forgot-password', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email }) });
    const data = await response.json();
    if (!response.ok) { setError(data.error ?? 'Unable to start password reset'); return; }
    if (data.reset_token) setResetToken(data.reset_token);
    setResetNotice(data.reset_token ? 'Development reset token generated. Enter a new password below.' : 'If the account exists, reset instructions were created.');
  }

  async function submitReset(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError('');
    const response = await fetch('http://localhost:5000/api/v1/auth/reset-password', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ token: resetToken, password: resetPassword }) });
    const data = await response.json();
    if (!response.ok) { setError(data.error ?? 'Unable to reset password'); return; }
    setResetNotice('Password reset complete. You can sign in with the new password.'); setResetOpen(false); setResetPassword('');
  }

  return (
    <main className="auth-shell">
      <section className="auth-story">
        <a className="brand auth-brand" href="#login" aria-label="TransferGuard">
          <span className="brand-mark">◈</span>
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
<div className="password-reset-entry"><button type="button" className="text-button" onClick={() => { setResetOpen(!resetOpen); setError('); setResetNotice('); }}>Forgot password?</button>{resetOpen && <form className="password-reset-form" onSubmit={submitReset}><input type="email" placeholder="Account email" value={email} onChange={(event) => setEmail(event.target.value)} required /><button type="button" onClick={() => void requestReset()}>Generate reset token</button>{resetToken && <input type="text" placeholder="Reset token" value={resetToken} onChange={(event) => setResetToken(event.target.value)} required />}<input type="password" placeholder="New password (12+ characters)" value={resetPassword} onChange={(event) => setResetPassword(event.target.value)} minLength={12} required /><button type="submit">Reset password</button>{resetNotice && <small>{resetNotice}</small>}</form>}</div>
          <div className="demo-account-choices">
            <button type="button" onClick={() => { setEmail(DEMO_USERS[0].email); setPassword(DEMO_PASSWORD); }}>{t.adminDemo}<span>admin@transferguard.demo</span></button>
            <button type="button" onClick={() => { setEmail(DEMO_USERS[1].email); setPassword(DEMO_PASSWORD); }}>{t.researcherDemo}<span>analyst@transferguard.demo</span></button>
            <button type="button" onClick={() => { setEmail(DEMO_USERS[2].email); setPassword(DEMO_PASSWORD); }}>Customer demo<span>customer@transferguard.demo</span></button>
            <button type="button" onClick={() => { setEmail(DEMO_USERS[3].email); setPassword(DEMO_PASSWORD); }}>Compliance demo<span>compliance@transferguard.demo</span></button>
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
  token: string;
};

export function UserManagement({ currentUser, language, token }: UserManagementProps & { language: Language }) {
  const t = getMessages(language);
  const [users, setUsers] = useState<SessionUser[]>([]);
  const authHeaders = { Authorization: 'Bearer ' + token, 'Content-Type': 'application/json' };
  useEffect(() => { fetch('http://localhost:5000/api/v1/users', { headers: authHeaders }).then(async (response) => { if (!response.ok) throw new Error((await response.json()).error ?? 'Unable to load users'); return response.json(); }).then(setUsers).catch((caught) => setError(caught instanceof Error ? caught.message : 'Unable to load users')); }, [token]);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<SessionUser['role']>('analyst');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [pendingDeleteId, setPendingDeleteId] = useState<number | null>(null);
  const [resetUserId, setResetUserId] = useState<number | null>(null);
  const [resetNewPassword, setResetNewPassword] = useState('');
  const [editingUserId, setEditingUserId] = useState<number | null>(null);
  const [editName, setEditName] = useState('');
  const [editEmail, setEditEmail] = useState('');
  const [createOpen, setCreateOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [roleFilter, setRoleFilter] = useState<'all' | SessionUser['role']>('all');
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'inactive'>('all');

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
      setRole('analyst');
      setCreateOpen(false);
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

  async function resetAccountPassword() {
    if (!resetUserId) return;
    try { const response = await fetch('http://localhost:5000/api/v1/users/' + resetUserId + '/reset-password', { method: 'POST', headers: authHeaders, body: JSON.stringify({ password: resetNewPassword }) }); const data = await response.json(); if (!response.ok) throw new Error(data.error); setResetUserId(null); setResetNewPassword(''); setNotice('Password updated successfully.'); } catch (caught) { setError(caught instanceof Error ? caught.message : String(caught)); }
  }

  const filteredUsers = useMemo(() => {
    const query = searchTerm.trim().toLowerCase();
    return users.filter((user) => {
      const matchesQuery = !query || `${user.name} ${user.email}`.toLowerCase().includes(query);
      const matchesRole = roleFilter === 'all' || user.role === roleFilter;
      const matchesStatus = statusFilter === 'all' || (statusFilter === 'active' ? user.active : !user.active);
      return matchesQuery && matchesRole && matchesStatus;
    });
  }, [users, searchTerm, roleFilter, statusFilter]);

  const editingUser = users.find((user) => user.id === editingUserId);

  async function requestReset() {
    setError(''); setResetNotice('');
    const response = await fetch('http://localhost:5000/api/v1/auth/forgot-password', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email }) });
    const data = await response.json();
    if (!response.ok) { setError(data.error ?? 'Unable to start password reset'); return; }
    if (data.reset_token) setResetToken(data.reset_token);
    setResetNotice(data.reset_token ? 'Development reset token generated. Enter a new password below.' : 'If the account exists, reset instructions were created.');
  }

  async function submitReset(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError('');
    const response = await fetch('http://localhost:5000/api/v1/auth/reset-password', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ token: resetToken, password: resetPassword }) });
    const data = await response.json();
    if (!response.ok) { setError(data.error ?? 'Unable to reset password'); return; }
    setResetNotice('Password reset complete. You can sign in with the new password.'); setResetOpen(false); setResetPassword('');
  }

  return (
    <section className="panel user-management" id="user-management">
      <div className="panel-heading user-management-heading">
        <div><h2>{t.userManagement}</h2><p>{t.workspaceAccounts}</p></div>
        <span className="record-count">{t.administrator}</span>
      </div>
      <div className="user-management-grid">
        <button type="button" className="user-add-trigger" onClick={() => setCreateOpen(true)}><span className="add-trigger-icon">+</span><span><strong>{t.createAccount}</strong><small>{t.addDemoAccount}</small></span></button>

        <div className="user-directory">
          <div className="user-directory-heading"><div className="directory-title"><strong>{t.workspaceDirectory}</strong><span className="directory-edit-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20h9" /><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L8 18l-4 1 1-4Z" /></svg></span></div><span>{users.length} {t.account}</span></div>          <div className="user-directory-controls"><label className="user-search"><span aria-hidden="true">⌕</span><input type="search" placeholder="Search users..." value={searchTerm} onChange={(event) => setSearchTerm(event.target.value)} /></label><select aria-label="Filter by role" value={roleFilter} onChange={(event) => setRoleFilter(event.target.value as typeof roleFilter)}><option value="all">All roles</option><option value="admin">Risk Manager / Admin</option><option value="analyst">Fraud Analyst</option><option value="customer">Cardholder / Customer</option><option value="compliance">Compliance Officer</option></select><select aria-label="Filter by status" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as typeof statusFilter)}><option value="all">All status</option><option value="active">Active</option><option value="inactive">Inactive</option></select></div>
          {error && <div className="user-feedback user-feedback-error" role="alert">{error}</div>}
          {notice && <div className="user-feedback" role="status">{notice}</div>}
          {filteredUsers.length === 0 ? <div className="user-empty">{users.length === 0 ? t.noDemoAccounts : "No matching users found."}</div> : (
            <div className="user-list">
              {filteredUsers.map((user) => (
                <article className="user-row" key={user.id}>
                  <div className="user-avatar">{user.name.split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase()}</div>
                  <div className="user-identity"><strong>{user.name}{user.id === currentUser.id ? <span className="you-tag">{t.you}</span> : null}</strong><span className="user-role-label">{roleLabel(user.role, language)}</span><span>{user.email}</span></div>
                  <div className="user-row-tools">
                    <select aria-label={`${t.role} ${user.name}`} value={user.role} disabled={user.id === currentUser.id} onChange={(event) => updateAccount(user.id, { role: event.target.value as SessionUser['role'] })}>
                      <option value="analyst">Fraud Analyst</option><option value="customer">Cardholder / Customer</option><option value="compliance">Compliance Officer</option><option value="admin">{t.administrator}</option>
                    </select>
                    <button type="button" className={`user-state-button ${user.active ? '' : 'is-inactive'}`} disabled={user.id === currentUser.id} onClick={() => updateAccount(user.id, { active: !user.active })}>
                      <i />{user.id === currentUser.id ? t.current : user.active ? t.active : t.inactive}
                    </button>
                    {pendingDeleteId === user.id ? (
                      <span className="delete-confirmation"><span>{t.deleteQuestion}</span><button type="button" onClick={() => deleteAccount(user.id)}>{t.confirm}</button><button type="button" onClick={() => setPendingDeleteId(null)}>{t.cancel}</button></span>
                    ) : (
                      <>
                        <button type="button" className="user-reset-button" title="Reset password" aria-label={`Reset password for ${user.name}`} onClick={() => { setResetUserId(user.id); setResetNewPassword('); setError('); }}>↻</button>
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
      {createOpen && (<div className="user-create-modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.currentTarget === event.target) setCreateOpen(false); }}><div className="user-create-modal" role="dialog" aria-modal="true" aria-labelledby="create-user-title"><div className="user-edit-modal-heading"><div><strong id="create-user-title">{t.createAccount}</strong><small>Create a role-based dashboard account</small></div><button type="button" className="modal-close-button" aria-label={t.cancel} onClick={() => setCreateOpen(false)}>×</button></div><form className="user-create-modal-form" onSubmit={createAccount}><label><span>{t.fullName}<span className="required-mark" aria-hidden="true"> *</span></span><input autoFocus value={name} onChange={(event) => setName(event.target.value)} required maxLength={100} /></label><label><span>{t.emailAddress}<span className="required-mark" aria-hidden="true"> *</span></span><input type="email" autoComplete="off" value={email} onChange={(event) => setEmail(event.target.value)} required maxLength={254} /></label><label><span>{t.temporaryPassword}<span className="required-mark" aria-hidden="true"> *</span></span><input type="password" autoComplete="new-password" value={password} onChange={(event) => setPassword(event.target.value)} required minLength={12} maxLength={200} /></label><label>{t.role}<select value={role} onChange={(event) => setRole(event.target.value as SessionUser['role'])}><option value="analyst">Fraud Analyst</option><option value="customer">Cardholder / Customer</option><option value="compliance">Compliance Officer</option><option value="admin">{t.administrator}</option></select></label>{error && <div className="user-feedback user-feedback-error" role="alert">{error}</div>}<div className="user-edit-modal-actions"><button type="button" className="modal-cancel-button" onClick={() => setCreateOpen(false)}>{t.cancel}</button><button type="submit" className="user-add-button">{t.createAccount}<span aria-hidden="true">+</span></button></div></form></div></div>)}      {resetUserId && (<div className="user-reset-modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.currentTarget === event.target) setResetUserId(null); }}><div className="user-reset-modal" role="dialog" aria-modal="true" aria-labelledby="reset-user-title"><div className="user-edit-modal-heading"><strong id="reset-user-title">Reset password</strong><button type="button" className="modal-close-button" onClick={() => setResetUserId(null)}>×</button></div><p>Set a new password for this account.</p><input type="password" autoFocus minLength={12} placeholder="New password (12+ characters)" value={resetNewPassword} onChange={(event) => setResetNewPassword(event.target.value)} /><div className="user-edit-modal-actions"><button type="button" className="modal-cancel-button" onClick={() => setResetUserId(null)}>Cancel</button><button type="button" className="modal-update-button" onClick={() => void resetAccountPassword()}>Update password</button></div></div></div>)}
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