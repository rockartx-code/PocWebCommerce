import { CommonModule } from '@angular/common';
import { Component, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { OnboardingService, TenantCreationResponse } from '../../shared/onboarding.service';
import { TenantContextService } from '../../shared/tenant-context.service';

interface WizardState {
  account: { adminEmail: string; displayName: string; password: string };
  store: { name: string; industry: string; currency: string };
  payment: { provider: string; publicKey: string; accessToken: string };
  branding: { domain: string; primaryColor: string; logoUrl: string };
}

@Component({
  selector: 'app-onboarding-wizard',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <section class="space-y-6">
      <header class="flex items-center justify-between">
        <div>
          <p class="text-xs uppercase tracking-[0.3rem] text-indigo-300">Nuevo tenant</p>
          <h2 class="text-2xl font-semibold">Asistente de onboarding</h2>
          <p class="text-sm text-slate-400">Registra la cuenta, define la tienda y llegá al back office listo para operar.</p>
        </div>
        <a routerLink="/" class="text-sm text-indigo-300 hover:text-indigo-200">Volver</a>
      </header>

      <ol class="grid md:grid-cols-5 gap-3 text-xs text-slate-300">
        <li
          *ngFor="let step of steps; index as idx"
          class="rounded-lg border px-3 py-2"
          [class.bg-indigo-500/20]="idx === currentStep()"
          [class.border-indigo-400]="idx === currentStep()"
          [class.border-slate-800]="idx !== currentStep()"
        >
          <p class="font-semibold text-white">{{ idx + 1 }}. {{ step }}</p>
          <p class="text-slate-400" *ngIf="idx === currentStep()">Completa los datos</p>
        </li>
      </ol>

      <div class="border border-slate-800 rounded-2xl bg-slate-900/60 p-6" [ngSwitch]="currentStep()">
        <div *ngSwitchCase="0" class="space-y-4">
          <h3 class="text-lg font-semibold">Cuenta administradora</h3>
          <p class="text-sm text-slate-400">Crearemos el usuario owner y su contraseña temporal.</p>
          <div class="grid md:grid-cols-3 gap-4">
            <label class="text-sm text-slate-300 space-y-1">
              Email corporativo
              <input
                [(ngModel)]="state.account.adminEmail"
                name="adminEmail"
                type="email"
                class="w-full px-3 py-2 rounded bg-slate-950 border border-slate-800"
                placeholder="admin@acme.io"
              />
            </label>
            <label class="text-sm text-slate-300 space-y-1">
              Nombre para mostrar
              <input
                [(ngModel)]="state.account.displayName"
                name="displayName"
                class="w-full px-3 py-2 rounded bg-slate-950 border border-slate-800"
                placeholder="Acme Owner"
              />
            </label>
            <label class="text-sm text-slate-300 space-y-1">
              Password inicial
              <input
                [(ngModel)]="state.account.password"
                name="password"
                type="text"
                class="w-full px-3 py-2 rounded bg-slate-950 border border-slate-800"
                placeholder="auto-generada si se deja vacía"
              />
            </label>
          </div>
        </div>

        <div *ngSwitchCase="1" class="space-y-4">
          <h3 class="text-lg font-semibold">Datos de la tienda</h3>
          <p class="text-sm text-slate-400">Nombre visible, industria y moneda por defecto.</p>
          <div class="grid md:grid-cols-3 gap-4">
            <label class="text-sm text-slate-300 space-y-1">
              Nombre de la marca
              <input
                [(ngModel)]="state.store.name"
                name="storeName"
                class="w-full px-3 py-2 rounded bg-slate-950 border border-slate-800"
                placeholder="Tienda Aurora"
              />
            </label>
            <label class="text-sm text-slate-300 space-y-1">
              Industria
              <input
                [(ngModel)]="state.store.industry"
                name="industry"
                class="w-full px-3 py-2 rounded bg-slate-950 border border-slate-800"
                placeholder="Retail"
              />
            </label>
            <label class="text-sm text-slate-300 space-y-1">
              Moneda principal
              <select [(ngModel)]="state.store.currency" name="currency" class="w-full px-3 py-2 rounded bg-slate-950 border border-slate-800">
                <option value="USD">USD</option>
                <option value="ARS">ARS</option>
                <option value="BRL">BRL</option>
              </select>
            </label>
          </div>
        </div>

        <div *ngSwitchCase="2" class="space-y-4">
          <h3 class="text-lg font-semibold">Pago con Mercado Pago</h3>
          <p class="text-sm text-slate-400">Conecta claves para preferencias y webhooks.</p>
          <div class="grid md:grid-cols-2 gap-4">
            <label class="text-sm text-slate-300 space-y-1">
              Public key
              <input
                [(ngModel)]="state.payment.publicKey"
                name="publicKey"
                class="w-full px-3 py-2 rounded bg-slate-950 border border-slate-800"
                placeholder="APP_USR-..."
              />
            </label>
            <label class="text-sm text-slate-300 space-y-1">
              Access token
              <input
                [(ngModel)]="state.payment.accessToken"
                name="accessToken"
                class="w-full px-3 py-2 rounded bg-slate-950 border border-slate-800"
                placeholder="APP_USR-..."
              />
            </label>
          </div>
        </div>

        <div *ngSwitchCase="3" class="space-y-4">
          <h3 class="text-lg font-semibold">Dominio y branding</h3>
          <p class="text-sm text-slate-400">Asignamos subdominio, color primario y logo CDN.</p>
          <div class="grid md:grid-cols-3 gap-4">
            <label class="text-sm text-slate-300 space-y-1">
              Subdominio
              <input
                [(ngModel)]="state.branding.domain"
                name="domain"
                class="w-full px-3 py-2 rounded bg-slate-950 border border-slate-800"
                placeholder="aurora.shop.example"
              />
            </label>
            <label class="text-sm text-slate-300 space-y-1">
              Color primario
              <input [(ngModel)]="state.branding.primaryColor" name="primaryColor" type="color" class="w-full h-10 rounded" />
            </label>
            <label class="text-sm text-slate-300 space-y-1">
              Logo (CDN)
              <input
                [(ngModel)]="state.branding.logoUrl"
                name="logoUrl"
                class="w-full px-3 py-2 rounded bg-slate-950 border border-slate-800"
                placeholder="https://cdn.../logo.png"
              />
            </label>
          </div>
        </div>

        <div *ngSwitchCase="4" class="space-y-4">
          <h3 class="text-lg font-semibold">Resumen</h3>
          <p class="text-sm text-slate-400">Verificá todo antes de crear el tenant.</p>
          <div class="grid md:grid-cols-2 gap-4 text-sm">
            <div class="p-4 border border-slate-800 rounded-xl bg-slate-950/50 space-y-2">
              <h4 class="font-semibold text-indigo-200">Cuenta y tienda</h4>
              <p><strong>Email:</strong> {{ state.account.adminEmail || 'pendiente' }}</p>
              <p><strong>Nombre:</strong> {{ state.account.displayName || 'Owner' }}</p>
              <p><strong>Tienda:</strong> {{ state.store.name || 'Sin nombre' }} ({{ state.store.industry || 'Industria' }})</p>
              <p><strong>Moneda:</strong> {{ state.store.currency }}</p>
            </div>
            <div class="p-4 border border-slate-800 rounded-xl bg-slate-950/50 space-y-2">
              <h4 class="font-semibold text-indigo-200">Pago y branding</h4>
              <p><strong>MP Public key:</strong> {{ state.payment.publicKey || 'no cargada' }}</p>
              <p><strong>Dominio:</strong> {{ state.branding.domain || 'pendiente' }}</p>
              <p><strong>Color primario:</strong>
                <span class="inline-flex items-center gap-2"><span class="w-4 h-4 rounded" [style.background]="state.branding.primaryColor"></span>{{ state.branding.primaryColor }}</span>
              </p>
              <p><strong>Logo:</strong> {{ state.branding.logoUrl || 'se usará placeholder' }}</p>
            </div>
          </div>
          <div *ngIf="result" class="p-4 border border-indigo-500/40 rounded-xl bg-indigo-500/10 text-sm text-indigo-100 space-y-1">
            <p class="font-semibold">Tenant creado</p>
            <p>TenantId: {{ result.tenant.tenantId }} | Backoffice: {{ result.urls.backoffice }}</p>
            <p>Admin: {{ result.adminUser.email }} / pass: {{ result.adminUser.temporaryPassword }}</p>
          </div>
          <div *ngIf="error" class="text-sm text-red-400">{{ error }}</div>
        </div>
      </div>

      <footer class="flex items-center justify-between">
        <button
          class="px-4 py-2 rounded-lg border border-slate-700 text-slate-200 hover:bg-slate-800 disabled:opacity-50"
          (click)="prev()"
          [disabled]="currentStep() === 0 || submitting"
        >
          Anterior
        </button>
        <div class="flex gap-3">
          <button
            *ngIf="currentStep() < steps.length - 1"
            class="px-4 py-2 rounded-lg bg-indigo-500 hover:bg-indigo-400 disabled:opacity-50"
            (click)="next()"
            [disabled]="!canContinue()"
          >
            Siguiente
          </button>
          <button
            *ngIf="currentStep() === steps.length - 1"
            class="px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50"
            (click)="completeOnboarding()"
            [disabled]="submitting || (!result && !canContinue())"
          >
            {{ submitting ? 'Creando tenant...' : 'Lanzar back office' }}
          </button>
        </div>
      </footer>
    </section>
  `
})
export class OnboardingWizardComponent {
  steps = ['Cuenta', 'Datos de tienda', 'Método de pago (MP)', 'Dominio y branding', 'Resumen'];
  currentStep = signal(0);
  submitting = false;
  error: string | null = null;
  result: TenantCreationResponse | null = null;

  state: WizardState = {
    account: { adminEmail: '', displayName: '', password: '' },
    store: { name: '', industry: '', currency: 'USD' },
    payment: { provider: 'mercadopago', publicKey: '', accessToken: '' },
    branding: { domain: '', primaryColor: '#6366f1', logoUrl: '' }
  };

  constructor(
    private onboarding: OnboardingService,
    private tenantContext: TenantContextService,
    private router: Router
  ) {}

  next() {
    if (this.currentStep() < this.steps.length - 1 && this.canContinue()) {
      this.currentStep.update((step) => step + 1);
    }
  }

  prev() {
    this.currentStep.update((step) => Math.max(step - 1, 0));
  }

  canContinue() {
    switch (this.currentStep()) {
      case 0:
        return !!this.state.account.adminEmail;
      case 1:
        return !!this.state.store.name && !!this.state.store.industry;
      case 2:
        return !!this.state.payment.publicKey && !!this.state.payment.accessToken;
      case 3:
        return !!this.state.branding.domain;
      default:
        return true;
    }
  }

  async completeOnboarding() {
    this.submitting = true;
    this.error = null;
    try {
      const tenantPayload = {
        name: this.state.store.name,
        industry: this.state.store.industry,
        currency: this.state.store.currency,
        paymentProvider: this.state.payment.provider,
        paymentKeys: {
          publicKey: this.state.payment.publicKey,
          accessToken: this.state.payment.accessToken
        },
        adminEmail: this.state.account.adminEmail,
        branding: {
          primaryColor: this.state.branding.primaryColor,
          domain: this.state.branding.domain,
          logoUrl: this.state.branding.logoUrl
        }
      };

      const tenant = await firstValueFrom(this.onboarding.createTenant(tenantPayload));
      await firstValueFrom(
        this.onboarding.createTenantUser(tenant.tenant.tenantId, {
          email: this.state.account.adminEmail,
          role: 'admin',
          temporaryPassword: this.state.account.password || undefined,
          displayName: this.state.account.displayName || 'Owner'
        })
      );
      this.result = tenant;
      this.tenantContext.setTenantId(tenant.tenant.tenantId);
      await this.router.navigate(['/admin'], { queryParams: { tenantId: tenant.tenant.tenantId } });
    } catch (err) {
      this.error = 'No pudimos crear el tenant. Intenta nuevamente.';
      console.error(err);
    } finally {
      this.submitting = false;
    }
  }
}
