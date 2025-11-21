import { CommonModule } from '@angular/common';
import { Component, OnInit, signal } from '@angular/core';
import { BillingSnapshot } from '../../shared/models';
import { UsageService } from '../../shared/usage.service';

@Component({
  selector: 'app-billing-ops',
  standalone: true,
  imports: [CommonModule],
  template: `
    <section class="space-y-4">
      <div class="flex items-center justify-between">
        <div>
          <p class="text-xs uppercase tracking-[0.3rem] text-indigo-300">Super Admin</p>
          <h2 class="text-2xl font-semibold">Control de suspensiones</h2>
          <p class="text-sm text-slate-400">Dashboard de facturación con alertas rápidas.</p>
        </div>
        <div class="text-sm text-slate-400">{{ tenants().length }} tenants monitoreados</div>
      </div>

      <div class="grid md:grid-cols-3 gap-4" *ngIf="tenants().length; else empty">
        <article *ngFor="let tenant of tenants()" class="border border-slate-800 rounded-xl p-4 bg-slate-900/60 space-y-3">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-indigo-200 font-semibold">{{ tenant.tenantId }}</p>
              <p class="text-xs text-slate-500">Próximo ciclo {{ tenant.nextBillingAt | date: 'shortDate' }}</p>
            </div>
            <span class="px-3 py-1 rounded-full text-xs" [class.bg-emerald-500/20]="tenant.status === 'active'" [class.bg-amber-500/20]="tenant.status === 'pending'" [class.bg-rose-500/20]="tenant.status === 'suspended'">
              {{ tenant.status }}
            </span>
          </div>
          <div class="text-sm text-slate-300 space-y-1">
            <p>Monto adeudado: {{ tenant.amountDue || 0 | currency: 'USD' }}</p>
            <p>Reintentos: {{ tenant.retryAttempts || 0 }}</p>
          </div>
          <div class="flex gap-2">
            <button class="px-3 py-2 rounded-lg bg-emerald-500/20 border border-emerald-400/40 text-emerald-100" (click)="activate(tenant)">
              Reactivar
            </button>
            <button class="px-3 py-2 rounded-lg bg-rose-500/20 border border-rose-400/40 text-rose-100" (click)="suspend(tenant)">
              Suspender
            </button>
          </div>
          <p *ngIf="tenant.status === 'suspended'" class="text-xs text-rose-300">Se enviará alerta a soporte y al tenant.</p>
        </article>
      </div>

      <ng-template #empty>
        <div class="border border-slate-800 rounded-xl p-6 text-center text-slate-400">Sin datos de facturación aún.</div>
      </ng-template>
    </section>
  `
})
export class BillingOpsComponent implements OnInit {
  tenants = signal<BillingSnapshot[]>([]);

  constructor(private readonly usageService: UsageService) {}

  ngOnInit(): void {
    this.usageService.adminBilling().subscribe((items) => this.tenants.set(items));
  }

  suspend(item: BillingSnapshot) {
    this.tenants.update((all) => all.map((tenant) => (tenant.tenantId === item.tenantId ? { ...tenant, status: 'suspended' } : tenant)));
  }

  activate(item: BillingSnapshot) {
    this.tenants.update((all) => all.map((tenant) => (tenant.tenantId === item.tenantId ? { ...tenant, status: 'active', retryAttempts: 0 } : tenant)));
  }
}
