import { useEffect, useState } from 'react';
import { AUTH_API_URL, apiError, authenticatedFetch, type SessionUser } from './auth';

type Card = {
  id: number;
  brand: string;
  last4: string;
  exp_month: number;
  exp_year: number;
  status: 'active' | 'blocked' | 'frozen' | 'expired' | 'cancelled';
};

export function CardManagement({ token, currentUser }: { token: string; currentUser: SessionUser }) {
  const [cards, setCards] = useState<Card[]>([]);
  const [number, setNumber] = useState('');
  const [month, setMonth] = useState('');
  const [year, setYear] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };

  async function loadCards() {
    const response = await authenticatedFetch(`${AUTH_API_URL}/api/v1/cards`, { headers });
    if (!response.ok) throw await apiError(response, 'Unable to load cards');
    setCards((await response.json() as { items: Card[] }).items);
  }

  useEffect(() => { void loadCards().catch((caught) => setError(caught instanceof Error ? caught.message : 'Unable to load cards')); }, [token]);

  async function createCard(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(''); setNotice('');
    const response = await authenticatedFetch(`${AUTH_API_URL}/api/v1/cards`, {
      method: 'POST', headers,
      body: JSON.stringify({ card_number: number, exp_month: Number(month), exp_year: Number(year) }),
    });
    if (!response.ok) { setError((await apiError(response, 'Unable to validate card')).message); return; }
    setNumber(''); setMonth(''); setYear(''); setNotice('Card validated and securely tokenized.'); await loadCards();
  }

  async function updateCard(id: number, status: Card['status']) {
    const response = await authenticatedFetch(`${AUTH_API_URL}/api/v1/cards/${id}`, { method: 'PATCH', headers, body: JSON.stringify({ status }) });
    if (!response.ok) { setError((await apiError(response, 'Unable to update card')).message); return; }
    await loadCards();
  }

  async function deleteCard(id: number) {
    if (!window.confirm('Delete this tokenized card record?')) return;
    const response = await authenticatedFetch(`${AUTH_API_URL}/api/v1/cards/${id}`, { method: 'DELETE', headers });
    if (!response.ok) { setError((await apiError(response, 'Unable to delete card')).message); return; }
    await loadCards();
  }

  return <section className="dashboard-card rounded-2xl border border-slate-800 bg-[#0d1d2c] p-6">
    <div><p className="text-[11px] font-bold uppercase tracking-[0.28em] text-cyan-300">Card security</p><h2 className="mt-2 text-2xl font-semibold text-white">Manage cards</h2><p className="mt-2 text-sm text-slate-400">Cards are Luhn-validated and stored as tokens. The raw card number is never returned or saved.</p></div>
    {error && <p role="alert" className="mt-4 rounded-lg bg-rose-400/10 p-3 text-sm text-rose-200">{error}</p>}
    {notice && <p role="status" className="mt-4 rounded-lg bg-emerald-400/10 p-3 text-sm text-emerald-200">{notice}</p>}
    <form onSubmit={createCard} className="mt-6 grid gap-3 md:grid-cols-[1fr_110px_110px_auto]">
      <input aria-label="Card number" value={number} onChange={(event) => setNumber(event.target.value)} placeholder="Card number" inputMode="numeric" required className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white" />
      <input aria-label="Expiry month" value={month} onChange={(event) => setMonth(event.target.value)} placeholder="MM" inputMode="numeric" required className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white" />
      <input aria-label="Expiry year" value={year} onChange={(event) => setYear(event.target.value)} placeholder="YYYY" inputMode="numeric" required className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white" />
      <button className="rounded-lg bg-cyan-300 px-4 py-2 text-sm font-bold text-[#08131f]">Validate card</button>
    </form>
    <div className="mt-6 space-y-2">{cards.length ? cards.map((card) => <article key={card.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-800 bg-slate-900/50 p-4"><div><p className="font-semibold text-white">{card.brand.toUpperCase()} •••• {card.last4}</p><p className="mt-1 text-xs text-slate-500">Expires {String(card.exp_month).padStart(2, '0')}/{card.exp_year}</p></div><div className="flex flex-wrap items-center justify-end gap-2"><span className={`rounded-full px-2 py-1 text-[10px] font-bold ${card.status === 'active' ? 'bg-emerald-400/10 text-emerald-300' : card.status === 'cancelled' || card.status === 'expired' ? 'bg-slate-400/10 text-slate-400' : 'bg-amber-400/10 text-amber-200'}`}>{card.status}</span>{card.status === 'active' && <><button onClick={() => void updateCard(card.id, 'frozen')} className="rounded-lg border border-amber-400/30 px-3 py-2 text-xs text-amber-200">Freeze</button><button onClick={() => void updateCard(card.id, 'blocked')} className="rounded-lg border border-rose-400/30 px-3 py-2 text-xs text-rose-200">Block</button></>}{(card.status === 'frozen' || card.status === 'blocked') && <button onClick={() => void updateCard(card.id, 'active')} className="rounded-lg border border-emerald-400/30 px-3 py-2 text-xs text-emerald-200">Activate</button>}{!['cancelled', 'expired'].includes(card.status) && <button onClick={() => void updateCard(card.id, 'cancelled')} className="rounded-lg border border-slate-700 px-3 py-2 text-xs text-slate-300">Cancel</button>}<button onClick={() => void deleteCard(card.id)} className="rounded-lg border border-rose-400/30 px-3 py-2 text-xs text-rose-200">Delete</button></div></article>) : <p className="py-8 text-center text-sm text-slate-500">No cards registered for {currentUser.email}.</p>}</div>
  </section>;
}
