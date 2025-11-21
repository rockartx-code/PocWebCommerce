import { Component } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <div class="min-h-screen bg-slate-950 text-slate-100">
      <header class="border-b border-slate-800/80 bg-slate-900/60 backdrop-blur sticky top-0 z-50">
        <div class="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between gap-4">
          <div class="flex items-center gap-3">
            <div class="h-10 w-10 rounded-lg bg-indigo-500/20 border border-indigo-400/50 flex items-center justify-center text-indigo-200 font-bold">AWS</div>
            <div>
              <p class="text-lg font-semibold">Poc Web Commerce</p>
              <p class="text-xs text-slate-400">Serverless + Angular 20 + Tailwind</p>
            </div>
          </div>
          <nav class="flex items-center gap-4 text-sm font-medium">
            <a routerLink="/" routerLinkActive="text-indigo-300" class="hover:text-indigo-200 transition-colors">Landing</a>
            <a routerLink="/catalog" routerLinkActive="text-indigo-300" class="hover:text-indigo-200 transition-colors">Catálogo</a>
            <a routerLink="/cart" routerLinkActive="text-indigo-300" class="hover:text-indigo-200 transition-colors">Carrito</a>
            <a routerLink="/analytics" routerLinkActive="text-indigo-300" class="hover:text-indigo-200 transition-colors">Analytics</a>
            <a routerLink="/admin" routerLinkActive="text-indigo-300" class="hover:text-indigo-200 transition-colors">Backoffice</a>
            <a routerLink="/auth" routerLinkActive="text-indigo-300" class="hover:text-indigo-200 transition-colors">Auth JWT</a>
          </nav>
        </div>
      </header>
      <main class="max-w-6xl mx-auto px-4 py-10 space-y-8">
        <router-outlet />
      </main>
      <footer class="border-t border-slate-800/80 bg-slate-900/60 py-6 text-center text-xs text-slate-400">
        Angular 20 · TailwindCSS · Cognito · API Gateway · DynamoDB · Mercado Pago
      </footer>
    </div>
  `
})
export class AppComponent {}
