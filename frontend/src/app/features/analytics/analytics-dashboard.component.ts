import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AnalyticsService } from '../../shared/analytics.service';
import { AnalyticsSnapshot } from '../../shared/models';

@Component({
  selector: 'app-analytics-dashboard',
  standalone: true,
  imports: [CommonModule],
  template: `
    <section class="space-y-6">
      <div>
        <p class="text-xs uppercase tracking-[0.3rem] text-indigo-300">Analytics</p>
        <h2 class="text-2xl font-semibold">Métricas de ventas y funnels</h2>
        <p class="text-sm text-slate-400">Simulación del consumo de GET /v1/analytics/sales.</p>
      </div>
      <div *ngIf="snapshot()" class="grid md:grid-cols-3 gap-4">
        <div class="border border-slate-800 rounded-xl p-4 bg-slate-900/50">
          <p class="text-sm text-slate-400">Ingresos {{ snapshot()!.period }}</p>
          <p class="text-3xl font-bold">{{ snapshot()!.revenue | currency : 'USD' }}</p>
        </div>
        <div class="border border-slate-800 rounded-xl p-4 bg-slate-900/50">
          <p class="text-sm text-slate-400">Órdenes</p>
          <p class="text-3xl font-bold">{{ snapshot()!.orders }}</p>
        </div>
        <div class="border border-slate-800 rounded-xl p-4 bg-slate-900/50">
          <p class="text-sm text-slate-400">Conversión</p>
          <p class="text-3xl font-bold">{{ snapshot()!.conversion }}%</p>
        </div>
      </div>
      <div *ngIf="snapshot()" class="border border-slate-800 rounded-xl p-4 bg-slate-900/50">
        <p class="text-sm text-slate-300 mb-3">Top productos</p>
        <div class="space-y-2">
          <div *ngFor="let top of snapshot()!.topProducts" class="flex items-center justify-between text-sm">
            <span>{{ top.name }}</span>
            <span class="text-indigo-200">{{ top.sales }} ventas</span>
          </div>
        </div>
      </div>
    </section>
  `
})
export class AnalyticsDashboardComponent implements OnInit {
  snapshot = signal<AnalyticsSnapshot | undefined>(undefined);

  constructor(private readonly analytics: AnalyticsService) {}

  ngOnInit(): void {
    this.analytics.metrics().subscribe((data) => this.snapshot.set(data));
  }
}
