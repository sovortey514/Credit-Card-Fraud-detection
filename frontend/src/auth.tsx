import React, { useEffect, useMemo, useState } from 'react';
import { getMessages, type Language } from './i18n';

export type SessionUser = {
  id: number;
  name: string;
  email: string;
  role: 'admin' | 'analyst' | 'customer' | 'compliance' | 'super_admin' | 'user';
  active: boolean;
  created_at: string | number;
};

export const DEMO_PASSWORD = 'transfer-demo-2026';
export const DEMO_USERS: SessionUser[] = [
  { id: 1, name: 'Risk Manager', email: 'admin@transferguard.demo', role: 'admin', active: true, created_at: 1761696000 },
  { id: 2, name: 'Fraud Analyst', email: 'analyst@transferguard.demo', role: 'analyst', active: true, created_at: 1761782400 },

  { id: 3, name: 'Cardholder Demo', email: 'customer@transferguard.demo', role: 'customer', active: true, created_at: 1761868800 },
  { id: 4, name: 'Compliance Officer', email: 'compliance@transferguard.demo', role: 'compliance', active: true, created_at: 1761955200 },];
export function roleLabel(role: SessionUser['role'], language: Language): string {
  const normalized = role === 'super_admin' ? 'admin' : role === 'user' ? 'analyst' : role;
  if (language === 'km') return ({ admin: 'អ្នកគ្រប់គ្រងហានិភ័យ', analyst: 'អ្នកវិភាគក្លែងបន្លំ', customer: 'អតិថិជន', compliance: 'មន្ត្រីអនុលោមភាព' })[normalized];
  return ({ admin: 'Risk Manager / Admin', analyst: 'Fraud Analyst', customer: 'Cardholder / Customer', compliance: 'Compliance Officer' })[normalized];
}

export const AUTH_API_URL = 'http://localhost:8001';
type ApiRole = 'super_admin' | 'admin' | 'user';
type ApiUser = { id: number; name: string; email: string; role: ApiRole; is_active: boolean; created_at: string; updated_at: string; last_login_at?: string | null };

export function toSessionUser(user: ApiUser): SessionUser {
  return { ...user, active: user.is_active, role: user.role === 'super_admin' ? 'super_admin' : user.role === 'admin' ? 'admin' : 'user' };
}

export function toApiRole(role: SessionUser['role']): ApiRole {
  return role === 'super_admin' ? 'super_admin' : role === 'admin' ? 'admin' : 'user';
}

export async function apiError(response: Response, fallback: string): Promise<Error> {
  const data = await response.json().catch(() => ({}));
  return new Error(data.detail ?? data.error ?? fallback);
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
  const [email, setEmail] = useState('admin@example.com');
  const [password, setPassword] = useState('');
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
    const response = await fetch(`${AUTH_API_URL}/api/v1/auth/forgot-password`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email }) });
    const data = await response.json();
    if (!response.ok) { setError(data.detail ?? data.error ?? 'Unable to start password reset'); return; }
    if (data.development_reset_token) setResetToken(data.development_reset_token);
    setResetNotice(data.development_reset_token ? 'Development reset token generated. Enter a new password below.' : 'If the account exists, reset instructions were created.');
  }

  async function submitReset(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError('');
    const response = await fetch(`${AUTH_API_URL}/api/v1/auth/reset-password`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ token: resetToken, password: resetPassword }) });
    const data = await response.json();
    if (!response.ok) { setError(data.detail ?? data.error ?? 'Unable to reset password'); return; }
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
<div className="password-reset-entry"><button type="button" className="text-button" onClick={() => { setResetOpen(!resetOpen); setError(''); setResetNotice(''); }}>Forgot password?</button>{resetOpen && <form className="password-reset-form" onSubmit={submitReset}><input type="email" placeholder="Account email" value={email} onChange={(event) => setEmail(event.target.value)} required /><button type="button" onClick={() => void requestReset()}>Generate reset token</button>{resetToken && <input type="text" placeholder="Reset token" value={resetToken} onChange={(event) => setResetToken(event.target.value)} required />}<input type="password" placeholder="New password (12+ characters)" value={resetPassword} onChange={(event) => setResetPassword(event.target.value)} minLength={12} required /><button type="submit">Reset password</button>{resetNotice && <small>{resetNotice}</small>}</form>}</div>
          
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
  const [users, setUsers] = useState<SessionUser[]>(() => DEMO_USERS.map((user) => ({ ...user })));
  const authHeaders = { Authorization: 'Bearer ' + token, 'Content-Type': 'application/json' };
  async function loadUsers() {
    const response = await fetch(`${AUTH_API_URL}/api/v1/users?skip=0&limit=200`, { headers: authHeaders });
    if (!response.ok) throw await apiError(response, 'Unable to load users');
    const data = await response.json() as { items: ApiUser[] };
    setUsers(data.items.map(toSessionUser));
  }
  useEffect(() => {
    void loadUsers().catch((caught) => setError(caught instanceof Error ? caught.message : 'Unable to load users'));
  }, [token]);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<SessionUser['role']>('analyst');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [pendingDeleteId, setPendingDeleteId] = useState<number | null>(null);
  const [pendingStatusChange, setPendingStatusChange] = useState<{ userId: number; nextActive: boolean } | null>(null);
  const [resetUserId, setResetUserId] = useState<number | null>(null);
  const [resetNewPassword, setResetNewPassword] = useState('');
  const [editingUserId, setEditingUserId] = useState<number | null>(null);
  const [editName, setEditName] = useState('');
  const [editEmail, setEditEmail] = useState('');
  const [createOpen, setCreateOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [roleFilter, setRoleFilter] = useState<'all' | SessionUser['role']>('all');
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'inactive'>('all');

  async function createAccount(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    setNotice('');
    try {
      if (password.length < 12) throw new Error(t.passwordTooShort);
      const response = await fetch(`${AUTH_API_URL}/api/v1/users`, { method: 'POST', headers: authHeaders, body: JSON.stringify({ name: name.trim(), email: email.trim().toLowerCase(), password, role: toApiRole(role) }) });
      if (!response.ok) throw await apiError(response, 'Unable to create user');
      const created = toSessionUser((await response.json() as { user: ApiUser }).user);
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

  async function updateAccount(userId: number, patch: { role?: SessionUser['role']; active?: boolean }) {
    setError('');
    setNotice('');
    try {
      const target = users.find((user) => user.id === userId);
      if (!target) throw new Error(t.accountNotFound);
      const nextRole = patch.role ?? target.role;
      const nextActive = patch.active ?? target.active;
      if (userId === currentUser.id && !nextActive) throw new Error(t.noSelfDeactivate);
      const response = await fetch(`${AUTH_API_URL}/api/v1/users/${userId}`, { method: 'PATCH', headers: authHeaders, body: JSON.stringify({ role: toApiRole(nextRole), is_active: nextActive }) });
      if (!response.ok) throw await apiError(response, 'Unable to update user');
      const updated = toSessionUser((await response.json() as { user: ApiUser }).user);
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

  async function saveEdit(userId: number) {
    const nextName = editName.trim();
    const nextEmail = editEmail.trim().toLowerCase();
    if (!nextName || !nextEmail) {
      setError('Full name and email address are required.');
      return;
    }
    const updated = users.find((user) => user.id === userId);
    if (!updated) {
      setError(t.accountNotFound);
      return;
    }
    try {
      const response = await fetch(`${AUTH_API_URL}/api/v1/users/${userId}`, { method: 'PATCH', headers: authHeaders, body: JSON.stringify({ name: nextName, email: nextEmail }) });
      if (!response.ok) throw await apiError(response, 'Unable to update user');
      const updatedUser = toSessionUser((await response.json() as { user: ApiUser }).user);
      setUsers((current) => current.map((user) => user.id === userId ? updatedUser : user));
      setEditingUserId(null);
      setEditName('');
      setEditEmail('');
      setNotice(`${t.accountUpdated} ${nextName}.`);
      setError('');
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    }
  }

  async function deleteAccount(userId: number) {
    setError('');
    setNotice('');
    const target = users.find((user) => user.id === userId);
    if (!target) return;
    if (userId === currentUser.id) {
      setError(t.noSelfDelete);
      return;
    }
    try {
      const response = await fetch(`${AUTH_API_URL}/api/v1/users/${userId}`, { method: 'DELETE', headers: authHeaders });
      if (response.status === 404) {
        await loadUsers();
        setPendingDeleteId(null);
        setNotice('That user no longer exists. The directory was refreshed.');
        return;
      }
      if (!response.ok) throw await apiError(response, 'Unable to delete user');
      setUsers((current) => current.filter((user) => user.id !== userId));
      setPendingDeleteId(null);
      setNotice(`${t.accountDeleted} ${target.name}.`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    }
  }

  async function resetAccountPassword() {
    if (!resetUserId) return;
    try { const response = await fetch(`${AUTH_API_URL}/api/v1/users/${resetUserId}/reset-password`, { method: 'POST', headers: authHeaders, body: JSON.stringify({ password: resetNewPassword }) }); if (!response.ok) throw await apiError(response, 'Unable to reset password'); setResetUserId(null); setResetNewPassword(''); setNotice('Password updated successfully.'); } catch (caught) { setError(caught instanceof Error ? caught.message : String(caught)); }
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
  const pendingDeleteUser = users.find((user) => user.id === pendingDeleteId);
  const pendingStatusUser = pendingStatusChange ? users.find((user) => user.id === pendingStatusChange.userId) : undefined;

  const editingUser = users.find((user) => user.id === editingUserId);

  return (
    <section className="panel user-management" id="user-management">
      <div className="panel-heading user-management-heading">
        <div><h2>{t.userManagement}</h2><p>{t.workspaceAccounts}</p></div>
        <span className="record-count">{t.administrator}</span>
      </div>
      <div className="user-management-grid">
        <button type="button" className="user-add-trigger" onClick={() => setCreateOpen(true)}><span className="add-trigger-icon">+</span><span><strong>{t.createAccount}</strong><small>{t.addDemoAccount}</small></span></button>

        <div className="user-directory">
          <div className="user-directory-heading"><div className="directory-title"><strong>{t.workspaceDirectory}</strong><span className="directory-edit-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20h9" /><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L8 18l-4 1 1-4Z" /></svg></span></div><span>{users.length} {t.account}</span></div>          <div className="user-directory-controls"><label className="user-search"><span aria-hidden="true">⌕</span><input type="search" placeholder="Search users..." value={searchTerm} onChange={(event) => setSearchTerm(event.target.value)} /></label><select aria-label="Filter by role" value={roleFilter} onChange={(event) => setRoleFilter(event.target.value as typeof roleFilter)}><option value="all">All roles</option><option value="super_admin">Super Admin</option><option value="admin">Risk Manager / Admin</option><option value="user">Standard User</option></select><select aria-label="Filter by status" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as typeof statusFilter)}><option value="all">All status</option><option value="active">Active</option><option value="inactive">Inactive</option></select></div>
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
                      <option value="super_admin">Super Admin</option><option value="admin">{t.administrator}</option><option value="user">Standard User</option>
                    </select>
                    <button type="button" className={`user-state-button ${user.active ? '' : 'is-inactive'}`} disabled={user.id === currentUser.id} onClick={() => setPendingStatusChange({ userId: user.id, nextActive: !user.active })}>
                      <i />{user.id === currentUser.id ? t.current : user.active ? t.active : t.inactive}
                    </button>
                    <button type="button" className="user-reset-button" title="Reset password" aria-label={`Reset password for ${user.name}`} onClick={() => { setResetUserId(user.id); setResetNewPassword(''); setError(''); }}>↻</button>
                    <button type="button" className="user-edit-button" title={`${t.edit} ${user.name}`} aria-label={`${t.edit} ${user.name}`} onClick={() => beginEdit(user)}><svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20h9" /><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L8 18l-4 1 1-4Z" /></svg></button>
                    <button type="button" className="user-delete-button" title={`${t.delete} ${user.name}`} aria-label={`${t.delete} ${user.name}`} disabled={user.id === currentUser.id} onClick={() => setPendingDeleteId(user.id)}>
                      <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M3 6h18M8 6V4h8v2m3 0-1 14H6L5 6m4 4v6m6-6v6" /></svg>
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </div>
      </div>
      {pendingDeleteUser && (
        <div className="delete-confirmation-backdrop" role="presentation" onMouseDown={(event) => { if (event.currentTarget === event.target) setPendingDeleteId(null); }}>
          <div className="delete-confirmation-modal" role="dialog" aria-modal="true" aria-labelledby="delete-confirmation-title">
            <div className="delete-confirmation-icon">!</div>
            <div><h2 id="delete-confirmation-title">Delete account?</h2><p>Are you sure you want to delete <strong>{pendingDeleteUser.name}</strong>? This action cannot be undone.</p></div>
            <div className="delete-confirmation-actions"><button type="button" className="modal-cancel-button" onClick={() => setPendingDeleteId(null)}>{t.cancel}</button><button type="button" className="delete-confirm-button" onClick={() => deleteAccount(pendingDeleteUser.id)}>{t.delete}</button></div>
          </div>
        </div>
      )}
      {pendingStatusUser && pendingStatusChange && (
        <div className="delete-confirmation-backdrop" role="presentation" onMouseDown={(event) => { if (event.currentTarget === event.target) setPendingStatusChange(null); }}>
          <div className="delete-confirmation-modal status-confirmation-modal" role="dialog" aria-modal="true" aria-labelledby="status-confirmation-title">
            <div className="status-confirmation-icon">↻</div>
            <div><h2 id="status-confirmation-title">{pendingStatusChange.nextActive ? 'Activate account?' : 'Deactivate account?'}</h2><p>{pendingStatusChange.nextActive ? 'This account will be able to sign in and access its assigned workspace.' : 'This account will no longer be able to sign in until it is activated again.'}</p></div>
            <div className="delete-confirmation-actions"><button type="button" className="modal-cancel-button" onClick={() => setPendingStatusChange(null)}>{t.cancel}</button><button type="button" className="status-confirm-button" onClick={() => { updateAccount(pendingStatusUser.id, { active: pendingStatusChange.nextActive }); setPendingStatusChange(null); }}>{pendingStatusChange.nextActive ? 'Activate' : 'Deactivate'}</button></div>
          </div>
        </div>
      )}
      {createOpen && (<div className="user-create-modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.currentTarget === event.target) setCreateOpen(false); }}><div className="user-create-modal" role="dialog" aria-modal="true" aria-labelledby="create-user-title"><div className="user-edit-modal-heading"><div><strong id="create-user-title">{t.createAccount}</strong><small>Create a role-based dashboard account</small></div><button type="button" className="modal-close-button" aria-label={t.cancel} onClick={() => setCreateOpen(false)}>×</button></div><form className="user-create-modal-form" onSubmit={createAccount}><label><span>{t.fullName}<span className="required-mark" aria-hidden="true"> *</span></span><input autoFocus value={name} onChange={(event) => setName(event.target.value)} required maxLength={100} /></label><label><span>{t.emailAddress}<span className="required-mark" aria-hidden="true"> *</span></span><input type="email" autoComplete="off" value={email} onChange={(event) => setEmail(event.target.value)} required maxLength={254} /></label><label><span>{t.temporaryPassword}<span className="required-mark" aria-hidden="true"> *</span></span><input type="password" autoComplete="new-password" value={password} onChange={(event) => setPassword(event.target.value)} required minLength={12} maxLength={200} /></label><label>{t.role}<select value={role} onChange={(event) => setRole(event.target.value as SessionUser['role'])}><option value="super_admin">Super Admin</option><option value="admin">{t.administrator}</option><option value="analyst">Standard User</option></select></label>{error && <div className="user-feedback user-feedback-error" role="alert">{error}</div>}<div className="user-edit-modal-actions"><button type="button" className="modal-cancel-button" onClick={() => setCreateOpen(false)}>{t.cancel}</button><button type="submit" className="user-add-button">{t.createAccount}<span aria-hidden="true">+</span></button></div></form></div></div>)}      {resetUserId && (<div className="user-reset-modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.currentTarget === event.target) setResetUserId(null); }}><div className="user-reset-modal" role="dialog" aria-modal="true" aria-labelledby="reset-user-title"><div className="user-edit-modal-heading"><strong id="reset-user-title">Reset password</strong><button type="button" className="modal-close-button" onClick={() => setResetUserId(null)}>×</button></div><p>Set a new password for this account.</p><input type="password" autoFocus minLength={12} placeholder="New password (12+ characters)" value={resetNewPassword} onChange={(event) => setResetNewPassword(event.target.value)} /><div className="user-edit-modal-actions"><button type="button" className="modal-cancel-button" onClick={() => setResetUserId(null)}>Cancel</button><button type="button" className="modal-update-button" onClick={() => void resetAccountPassword()}>Update password</button></div></div></div>)}
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
