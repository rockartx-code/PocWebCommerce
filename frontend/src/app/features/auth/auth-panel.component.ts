import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../shared/auth.service';

@Component({
  selector: 'app-auth-panel',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <section class="space-y-4">
      <div>
        <p class="text-xs uppercase tracking-[0.3rem] text-indigo-300">Autenticación Cognito</p>
        <h2 class="text-2xl font-semibold">Gestiona tu Access Token</h2>
        <p class="text-sm text-slate-400">Los endpoints protegidos requieren Authorization: Bearer &lt;JWT&gt;.</p>
      </div>
      <div class="border border-slate-800 rounded-xl p-6 bg-slate-900/60 space-y-4">
        <textarea
          [(ngModel)]="token"
          rows="6"
          placeholder="Pega aquí tu Access Token de Cognito"
          class="w-full rounded-lg bg-slate-950 border border-slate-800 px-3 py-2 text-sm"
        ></textarea>
        <div class="flex gap-3">
          <button class="px-4 py-2 rounded-lg bg-indigo-500 hover:bg-indigo-400" (click)="persist()">Guardar token</button>
          <button class="px-4 py-2 rounded-lg border border-slate-700 hover:bg-slate-800" (click)="clear()">Limpiar</button>
        </div>
        <div class="text-xs text-slate-400">
          {{ auth.authorizationHeader | json }}
        </div>
      </div>
    </section>
  `
})
export class AuthPanelComponent {
  token = '';

  constructor(public readonly auth: AuthService) {
    this.token = this.auth.token() ?? '';
  }

  persist() {
    if (this.token.trim().length) {
      this.auth.setToken(this.token.trim());
    }
  }

  clear() {
    this.token = '';
    this.auth.clear();
  }
}
