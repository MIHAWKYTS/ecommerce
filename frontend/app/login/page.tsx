"use client";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { Alert } from "@/components/States";
import { api, User } from "@/lib/api";
import { useStore } from "../store";

type AuthOut = { session_id: string; user: User & { email: string } };

function safeNext(n: string | null) {
  return n && n.startsWith("/") && !n.startsWith("//") && !n.startsWith("/login") ? n : "/";
}

function LoginForm() {
  const params = useSearchParams();
  const router = useRouter();
  const { signIn } = useStore();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [f, setF] = useState({ name: "", email: "", password: "" });
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const next = safeNext(params.get("next"));

  async function submit(e: React.FormEvent) {
    e.preventDefault(); setErr(""); setBusy(true);
    try {
      const body = mode === "login" ? { email: f.email, password: f.password } : f;
      const r = await api<AuthOut>(`/auth/${mode}`, { method: "POST", body: JSON.stringify(body) });
      signIn(r.session_id, { id: r.user.id, name: r.user.name });
      router.push(next);
    } catch (e) {
      setErr((e as Error).message === "Credenciais inválidas" ? "E-mail ou senha incorretos." : (e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const tab = (m: typeof mode, label: string) => (
    <button type="button" role="tab" aria-selected={mode === m} onClick={() => { setMode(m); setErr(""); }}
      className={`flex-1 cursor-pointer border-b-2 pb-3 text-sm font-semibold transition ${mode === m ? "border-brand-600 text-brand-600" : "border-transparent text-muted hover:text-ink"}`}>
      {label}
    </button>
  );

  return (
    <div className="mx-auto w-full max-w-md">
      <div className="card p-6 md:p-8">
        <div role="tablist" className="mb-6 flex gap-4 border-b border-line">
          {tab("login", "Entrar")}
          {tab("register", "Criar conta")}
        </div>
        <h1 className="sr-only">{mode === "login" ? "Entrar" : "Criar conta"}</h1>

        <div className="mb-4 space-y-3 empty:hidden">
          {params.get("expirada") && <Alert tone="info">Sua sessão expirou. Entre de novo para continuar.</Alert>}        </div>

        <form onSubmit={submit} className="space-y-4">
          {mode === "register" && (
            <div>
              <label htmlFor="name" className="label">Nome</label>
              <input id="name" className="field" required maxLength={150} autoComplete="name"
                value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} />
            </div>
          )}
          <div>
            <label htmlFor="email" className="label">E-mail</label>
            <input id="email" type="email" className="field" required autoComplete="email"
              value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} />
          </div>
          <div>
            <label htmlFor="password" className="label">Senha</label>
            <input id="password" type="password" className="field" required minLength={6} maxLength={128}
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} />
            {mode === "register" && <p className="mt-1 text-xs text-muted">Mínimo de 6 caracteres.</p>}
          </div>
          {err && <Alert tone="error">{err}</Alert>}
          <button type="submit" className="btn-primary w-full" disabled={busy}>
            {busy ? "Aguarde…" : mode === "login" ? "Entrar" : "Cadastrar"}
          </button>
        </form>
      </div>
    </div>
  );
}

export default function Login() {
  return <Suspense fallback={<div className="card mx-auto h-80 max-w-md animate-pulse" />}><LoginForm /></Suspense>;
}
