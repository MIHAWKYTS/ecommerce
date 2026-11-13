import "./globals.css";
import type { Metadata } from "next";
import Header from "@/components/Header";
import { StoreProvider } from "./store";

export const metadata: Metadata = { title: "Loja BD II", description: "E-commerce de alto tráfego: PostgreSQL + Redis" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body className="flex min-h-screen flex-col">
        <StoreProvider>
          <Header />
          <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6">{children}</main>
          <footer className="border-t border-line bg-white">
            <div className="mx-auto max-w-6xl px-4 py-5 text-xs text-muted">
              Projeto acadêmico de Banco de Dados II (UFAL) · PostgreSQL 16 + Redis 7 · pagamento simulado
            </div>
          </footer>
        </StoreProvider>
      </body>
    </html>
  );
}
