import { CommonModule } from '@angular/common';
import { Component, OnInit, signal } from '@angular/core';
import { UsageService } from '../../shared/usage.service';
import { BillingSnapshot, TenantUsageSnapshot } from '../../shared/models';
import { TenantContextService } from '../../shared/tenant-context.service';

@Component({
  selector: 'app-tenant-usage',
  standalone: true,
  imports: [CommonModule],
  template: `
    <section class="space-y-6" *ngIf="usage() && billing()">
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div>
          <p class="text-xs uppercase tracking-[0.3rem] text-indigo-300">Uso y facturación</p>
          <h2 class="text-2xl font-semibold">Tenant {{ usage()!.tenantId }}</h2>
          <p class="text-sm text-slate-400">Panel de consumo por requests, órdenes, GMV y bytes.</p>
        </div>
        <div class="text-right text-sm text-slate-400">
          <p>Próximo cobro: {{ billing()!.nextBillingAt | date: 'short' }}</p>
          <p [class.text-emerald-300]="billing()!.status === 'active'" [class.text-amber-300]="billing()!.status === 'pending'" [class.text-rose-300]="billing()!.status === 'suspended'">
            Estado: {{ billing()!.status }}
          </p>
        </div>
      </div>

      <div class="grid md:grid-cols-4 gap-4" *ngIf="usage()">
        <div *ngFor="let metric of metricKeys" class="border border-slate-800 rounded-xl p-4 bg-slate-900/50">
          <p class="text-xs uppercase tracking-[0.2rem] text-slate-400">{{ metric }}</p>
          <p class="text-3xl font-semibold text-indigo-100">{{ usage()!.summary[metric] | number: '1.0-0' }}</p>
        </div>
      </div>

      <div class="grid md:grid-cols-2 gap-4" *ngIf="usage()!.history.length">
        <div class="border border-slate-800 rounded-xl p-4 bg-slate-900/50">
          <p class="text-sm text-slate-300 mb-3">Histórico diario</p>
          <ul class="space-y-2 text-sm">
            <li *ngFor="let item of usage()!.history" class="flex items-center justify-between">
              <div>
                <p class="text-indigo-200 font-semibold">{{ item.period }}</p>
                <p class="text-slate-400">{{ item.usage.requests }} requests · {{ item.usage.orders }} órdenes</p>
              </div>
              <div class="text-right">
                <p class="text-slate-300">GMV {{ item.usage.gmv | currency: 'USD' }}</p>
                <p class="text-slate-500 text-xs">{{ item.createdAt | date: 'short' }}</p>
              </div>
            </li>
          </ul>
        </div>
        <div class="border border-slate-800 rounded-xl p-4 bg-slate-900/50 space-y-3">
          <p class="text-sm text-slate-300">Estado de facturación</p>
          <div class="text-sm text-slate-200">
            <p>Próximo ciclo: {{ billing()!.nextBillingAt | date: 'mediumDate' }}</p>
            <p>Intentos de cobro: {{ billing()!.retryAttempts || 0 }}</p>
            <p>Monto estimado: {{ billing()!.amountDue || 0 | currency: 'USD' }}</p>
            <p class="text-slate-400">Último pago: {{ billing()!.lastPayment | date: 'short' }}</p>
          </div>
          <div class="text-xs text-slate-500">Los datos se obtienen de los endpoints protegidos /usage y /billing.</div>
        </div>
      </div>
    </section>
  `
})
export class TenantUsageComponent implements OnInit {
  usage = signal<TenantUsageSnapshot | null>(null);
  billing = signal<BillingSnapshot | null>(null);
  metricKeys = ['requests', 'orders', 'gmv', 'bytes'];

  constructor(private readonly usageService: UsageService, private readonly tenantContext: TenantContextService) {}

  ngOnInit(): void {
    const tenant = this.tenantContext.tenantId() || 'public';
    this.usageService.usage(tenant).subscribe((snapshot) => this.usage.set(snapshot));
    this.usageService.billing(tenant).subscribe((bill) => this.billing.set(bill));
  }
}
