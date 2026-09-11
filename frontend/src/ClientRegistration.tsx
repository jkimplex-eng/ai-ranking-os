import { useState } from "react";
import type { ApiClient } from "./api";

export function ClientRegistration({api}: {api: ApiClient}) {
  const [token, setToken] = useState(() => new URLSearchParams(window.location.hash.slice(1)).get("invite") || "");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  async function register() {
    setError("");
    if (password !== confirmation) {setError("Пароли не совпадают."); return;}
    setBusy(true);
    try {
      const result = await api.acceptClientInvitation(token.trim(), name.trim(), password);
      setMessage(`Аккаунт ${result.email} создан. Войдите с вашим паролем выше.`);
      setPassword(""); setConfirmation(""); setToken("");
      window.history.replaceState(null, "", window.location.pathname + window.location.search);
    } catch {setError("Не удалось зарегистрироваться. Проверьте приглашение: оно могло истечь или уже быть использовано.");}
    finally {setBusy(false);}
  }
  return <details open={Boolean(token) || undefined}>
    <summary>Как зарегистрироваться</summary>
    <p>Регистрация пока по приглашению владельца платформы. Email берётся из приглашения; оплата при регистрации не списывается.</p>
    {message ? <p role="status">{message}</p> : <form onSubmit={e => {e.preventDefault(); void register();}}>
      <label>Код приглашения<input type="password" autoComplete="off" required value={token} onChange={e => setToken(e.target.value)} /></label>
      <label>Ваше имя<input required maxLength={200} autoComplete="name" value={name} onChange={e => setName(e.target.value)} /></label>
      <label>Новый пароль<input type="password" required minLength={8} maxLength={1024} autoComplete="new-password" value={password} onChange={e => setPassword(e.target.value)} /></label>
      <label>Повторите пароль<input type="password" required minLength={8} autoComplete="new-password" value={confirmation} onChange={e => setConfirmation(e.target.value)} /></label>
      {error && <p role="alert">{error}</p>}
      <button disabled={busy}>{busy ? "Создаём аккаунт…" : "Зарегистрироваться"}</button>
    </form>}
  </details>;
}
