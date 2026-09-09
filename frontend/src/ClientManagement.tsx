import { useEffect, useState } from "react";
import type { AdminUser, ApiClient, ClientLimits, Tariff } from "./api";

const fields: Array<[keyof ClientLimits, string, number, number]> = [
  ["daily_research_limit", "Исследований в день", 0, 10000],
  ["monthly_research_limit", "Исследований в месяц", 0, 100000],
  ["max_projects", "Проектов", 0, 10000],
  ["max_domains", "Доменов", 0, 100000],
  ["max_organization_users", "Сотрудников", 1, 10000],
];

export function ClientManagement({api}: {api: ApiClient}) {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<AdminUser>();
  const [limits, setLimits] = useState<ClientLimits>();
  const [saving, setSaving] = useState(false);
  const [tariffs, setTariffs] = useState<Tariff[]>([]);
  const [planCode, setPlanCode] = useState("trial");
  const [subscriptionStatus, setSubscriptionStatus] = useState("NONE");
  const [subscriptionEndsAt, setSubscriptionEndsAt] = useState("");
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteLink, setInviteLink] = useState("");
  const [inviting, setInviting] = useState(false);
  async function invite() {
    setInviting(true); setError(""); setInviteLink("");
    try {
      const result = await api.createClientInvitation(inviteEmail.trim());
      setInviteLink(`${window.location.origin}/#invite=${encodeURIComponent(result.token)}`);
    } catch {setError("Приглашение не создано. Проверьте email: аккаунт мог быть зарегистрирован ранее.");}
    finally {setInviting(false);}
  }
  useEffect(() => {
    let cancelled = false;
    setLoading(true); setError("");
    api.adminUsers(search).then(items => {if (!cancelled) setUsers(items);})
      .catch(() => {if (!cancelled) setError("Не удалось загрузить клиентов. Проверьте доступ администратора платформы.");})
      .finally(() => {if (!cancelled) setLoading(false);});
    return () => {cancelled = true;};
  }, [api, search]);
  useEffect(() => { api.adminTariffs().then(setTariffs).catch(() => setError("Не удалось загрузить тарифы.")); }, [api]);
  async function save() {
    if (!selected || !limits) return;
    setSaving(true); setError(""); setMessage("");
    try {
      const updated = await api.updateClientLimits(selected.user_id, limits);
      setUsers(items => items.map(item => item.user_id === updated.user_id ? updated : item));
      setSelected(updated); setMessage(`Лимиты ${updated.email} сохранены. Изменение записано в журнал.`);
    } catch {setError("Лимиты не сохранены. Проверьте значения и повторите попытку.");}
    finally {setSaving(false);}
  }
  async function saveSubscription() {
    if (!selected) return;
    setSaving(true); setError(""); setMessage("");
    try {
      const updated = await api.updateClientSubscription(selected.user_id, {
        plan_code: planCode, status: subscriptionStatus,
        starts_at: subscriptionStatus === "NONE" ? null : new Date().toISOString(),
        ends_at: subscriptionEndsAt ? new Date(`${subscriptionEndsAt}T23:59:59`).toISOString() : null,
        apply_plan_limits: true,
      });
      setUsers(items => items.map(item => item.user_id === updated.user_id ? updated : item));
      setSelected(updated); setLimits(updated.limits ? {...updated.limits} : undefined);
      setMessage(`Подписка ${updated.email} обновлена, лимиты тарифа применены.`);
    } catch { setError("Подписка не сохранена. Проверьте тариф, статус и дату."); }
    finally { setSaving(false); }
  }
  return <section className="analytics-card" aria-label="Управление клиентами">
    <h2>Клиенты, подписки и лимиты</h2>
    <div className="admin-summary"><strong>{users.length}</strong><p>клиентов в текущей выборке · активных подписок: {users.filter(user => user.subscription?.status === "ACTIVE").length}</p></div>
    <form onSubmit={e => {e.preventDefault(); void invite();}}>
      <label>Email нового клиента<input type="email" required value={inviteEmail} onChange={e => setInviteEmail(e.target.value)} /></label>
      <button disabled={inviting}>{inviting ? "Создаём приглашение…" : "Создать приглашение"}</button>
    </form>
    {inviteLink && <div role="status"><p>Отправьте ссылку клиенту самостоятельно. Письмо автоматически не отправлялось. Ссылка действует 72 часа, храните её как секрет.</p><input aria-label="Ссылка регистрации" readOnly value={inviteLink} onFocus={e => e.target.select()} /></div>}
    <p>Лимиты доступа — не оплаченная подписка. Эта форма не выполняет списания и не подтверждает оплату.</p>
    <label>Поиск клиента<input value={search} onChange={e => setSearch(e.target.value)} /></label>
    {error && <p role="alert">{error}</p>}{message && <p role="status">{message}</p>}
    {loading ? <p>Загружаем клиентов…</p> : !error && !users.length ? <p>Клиенты не найдены.</p> : users.map(user => <article className="resource-proof" key={user.user_id}>
      <h3>{user.display_name}</h3><p>{user.email} · Исследований: {user.research_count}</p>
      <p><b>{user.subscription?.plan_name ?? "Без тарифа"}</b> · {user.subscription?.status ?? "NONE"}{user.subscription?.ends_at ? ` · до ${new Date(user.subscription.ends_at).toLocaleDateString("ru-RU")}` : ""}</p>
      <button disabled={saving || !user.limits} onClick={() => {setSelected(user); setLimits(user.limits ? {...user.limits} : undefined); setPlanCode(user.subscription?.plan_code ?? "trial"); setSubscriptionStatus(user.subscription?.status ?? "NONE"); setSubscriptionEndsAt(user.subscription?.ends_at?.slice(0, 10) ?? ""); setMessage("");}}>Управлять клиентом</button>
    </article>)}
    {selected && limits && <form onSubmit={e => {e.preventDefault(); void save();}}>
      <h3>Клиент: {selected.email}</h3>
      <label>Тариф<select value={planCode} disabled={saving} onChange={e => setPlanCode(e.target.value)}>{tariffs.map(tariff => <option key={tariff.code} value={tariff.code}>{tariff.name} — {tariff.monthly_price_rub.toLocaleString("ru-RU")} ₽/мес.</option>)}</select></label>
      <label>Статус подписки<select value={subscriptionStatus} disabled={saving} onChange={e => setSubscriptionStatus(e.target.value)}><option value="NONE">Нет подписки</option><option value="TRIAL">Пробный период</option><option value="ACTIVE">Активна</option><option value="PAST_DUE">Ожидает оплаты</option><option value="PAUSED">Приостановлена</option><option value="CANCELED">Отменена</option></select></label>
      <label>Действует до<input type="date" value={subscriptionEndsAt} disabled={saving} onChange={e => setSubscriptionEndsAt(e.target.value)} /></label>
      <button type="button" disabled={saving} onClick={() => void saveSubscription()}>{saving ? "Сохраняем…" : "Применить тариф и подписку"}</button>
      <p>{selected.subscription?.checkout_message}</p>
      <h3>Индивидуальные лимиты</h3>
      {fields.map(([key, label, min, max]) => <label key={key}>{label}<input type="number" required min={min} max={max} step={1} disabled={saving} value={limits[key]} onChange={e => setLimits({...limits, [key]: e.target.valueAsNumber})} /></label>)}
      <button disabled={saving}>{saving ? "Сохраняем…" : "Сохранить лимиты"}</button>
      <button type="button" disabled={saving} onClick={() => setSelected(undefined)}>Закрыть</button>
    </form>}
    <small>Показаны первые 50 найденных клиентов. Для поиска конкретного клиента используйте email.</small>
  </section>;
}
