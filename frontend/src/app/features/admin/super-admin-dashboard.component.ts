import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { TenantUsageRecord, TenantUsageResponse } from '../../shared/models';
import { SuperAdminService, TenantUsageFilters } from '../../shared/super-admin.service';

@Component({
  selector: 'app-super-admin-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <section class="space-y-6">
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div>
          <p class="text-xs uppercase tracking-[0.3rem] text-indigo-300">Super Admin</p>
          <h2 class="text-2xl font-semibold">Uso agregado por tenant</h2>
          <p class="text-sm text-slate-400">Lectura de /v1/admin/tenants/usage con filtros y paginación.</p>
        </div>
        <div class="text-right text-sm text-slate-400">
          <p>Períodos consolidados: {{ usage()?.total || 0 }}</p>
          <p *ngIf="alerts().length" class="text-amber-300">{{ alerts().length }} alertas de consumo</p>
        </div>
      </div>

      <form (ngSubmit)="applyFilters()" class="grid md:grid-cols-4 gap-4 items-end">
        <label class="flex flex-col text-sm text-slate-300 gap-1">
          Desde
          <input [(ngModel)]="formState.startDate" name="startDate" type="date" class="px-3 py-2 rounded-lg bg-slate-900 border border-slate-800" />
        </label>
        <label class="flex flex-col text-sm text-slate-300 gap-1">
          Hasta
          <input [(ngModel)]="formState.endDate" name="endDate" type="date" class="px-3 py-2 rounded-lg bg-slate-900 border border-slate-800" />
        </label>
        <label class="flex flex-col text-sm text-slate-300 gap-1">
          Tamaño de página
          <select [(ngModel)]="formState.pageSize" name="pageSize" class="px-3 py-2 rounded-lg bg-slate-900 border border-slate-800">
            <option [value]="5">5</option>
            <option [value]="10">10</option>
            <option [value]="20">20</option>
          </select>
        </label>
        <div class="flex flex-col gap-2 text-sm text-slate-300">
          Métricas
          <div class="grid grid-cols-2 gap-2">
            <label *ngFor="let metric of metricOptions" class="flex items-center gap-2">
              <input type="checkbox" [checked]="metricSelected(metric)" (change)="toggleMetric(metric, $event.target.checked)" />
              <span class="capitalize">{{ metric }}</span>
            </label>
          </div>
        </div>
        <div class="md:col-span-4 flex items-center gap-3">
          <button type="submit" class="px-4 py-2 rounded-lg bg-indigo-500 hover:bg-indigo-400 disabled:opacity-50" [disabled]="loading()">
            Aplicar filtros
          </button>
          <span *ngIf="loading()" class="text-sm text-slate-400">Actualizando métricas...</span>
        </div>
      </form>

      <div *ngIf="alerts().length" class="bg-amber-500/10 border border-amber-400/40 text-amber-100 rounded-xl p-4 space-y-2">
        <p class="text-sm font-semibold">Alertas de consumo</p>
        <ul class="text-sm list-disc list-inside space-y-1">
          <li *ngFor="let alert of alerts()">{{ alert }}</li>
        </ul>
      </div>

      <div class="grid md:grid-cols-2 gap-4" *ngIf="usage()?.items.length; else emptyState">
        <article *ngFor="let item of usage()?.items" class="border border-slate-800 rounded-xl bg-slate-900/60 p-4 space-y-3">
          <div class="flex items-center justify-between text-sm text-slate-400">
            <div>
              <p class="uppercase text-xs tracking-[0.2rem] text-indigo-300">{{ item.period }}</p>
              <p class="text-lg text-slate-100 font-semibold">{{ item.tenantId }}</p>
            </div>
            <div class="text-right">
              <p class="text-xs">Registrado: {{ item.createdAt | date: 'short' }}</p>
              <p class="text-xs text-slate-500">{{ selectedMetrics().length }} métricas</p>
            </div>
          </div>
          <div class="space-y-3">
            <div *ngFor="let metric of selectedMetrics()" class="space-y-1">
              <div class="flex items-center justify-between text-xs text-slate-400">
                <span class="uppercase tracking-[0.2rem]">{{ metric }}</span>
                <span class="text-indigo-200 font-semibold">{{ item.usage[metric] | number: '1.0-0' }}</span>
              </div>
              <div class="h-2 rounded-full bg-slate-800 overflow-hidden">
                <div class="h-2 bg-indigo-500" [style.width]="barWidth(item, metric)"></div>
              </div>
            </div>
          </div>
        </article>
      </div>

      <ng-template #emptyState>
        <div class="border border-slate-800 rounded-xl p-6 text-center text-slate-400">No hay métricas disponibles para este filtro.</div>
      </ng-template>

      <div class="flex items-center justify-between text-sm text-slate-400" *ngIf="usage()">
        <div>Mostrando página {{ usage()!.page }} de {{ totalPages() }}</div>
        <div class="flex gap-2">
          <button class="px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-50" (click)="changePage(-1)" [disabled]="usage()!.page <= 1 || loading()">
            Anterior
          </button>
          <button class="px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-50" (click)="changePage(1)" [disabled]="usage()!.page >= totalPages() || loading()">
            Siguiente
          </button>
        </div>
      </div>
    </section>
  `
})
export class SuperAdminDashboardComponent implements OnInit {
  usage = signal<TenantUsageResponse | null>(null);
  loading = signal(false);
  metricOptions = ['requests', 'orders', 'gmv', 'bytes'];
  metricSelection = signal<Set<string>>(new Set(this.metricOptions));
  formState = { startDate: '', endDate: '', pageSize: 5 };

  constructor(private readonly adminService: SuperAdminService) {}

  ngOnInit(): void {
    this.load();
  }

  selectedMetrics = computed(() => Array.from(this.metricSelection()));

  totalPages = computed(() => {
    const data = this.usage();
    if (!data || !data.pageSize) return 1;
    return Math.max(1, Math.ceil(data.total / data.pageSize));
  });

  alerts = computed(() => {
    const data = this.usage();
    if (!data) return [] as string[];
    return data.items
      .filter((item) => (item.usage.requests ?? 0) > 300 || (item.usage.gmv ?? 0) > 20000)
      .map((item) => `Tenant ${item.tenantId} supera el umbral con ${item.usage.requests || 0} requests y GMV ${item.usage.gmv || 0}`);
  });

  metricSelected(metric: string): boolean {
    return this.metricSelection().has(metric);
  }

  toggleMetric(metric: string, checked: boolean) {
    const next = new Set(this.metricSelection());
    if (checked) {
      next.add(metric);
    } else {
      next.delete(metric);
    }
    if (!next.size) {
      next.add(metric);
    }
    this.metricSelection.set(next);
  }

  applyFilters() {
    this.load(1);
  }

  changePage(delta: number) {
    const current = this.usage();
    if (!current) return;
    const nextPage = current.page + delta;
    if (nextPage < 1 || nextPage > this.totalPages()) return;
    this.load(nextPage);
  }

  load(page: number = 1) {
    this.loading.set(true);
    const filters: TenantUsageFilters = {
      startDate: this.formState.startDate || undefined,
      endDate: this.formState.endDate || undefined,
      metrics: this.selectedMetrics(),
      page,
      pageSize: this.formState.pageSize,
    };
    this.adminService.usage(filters).subscribe((response) => {
      this.usage.set(response);
      this.loading.set(false);
    });
  }

  barWidth(record: TenantUsageRecord, metric: string): string {
    const max = this.maxValue(metric);
    const value = record.usage[metric] || 0;
    if (!max) return '10%';
    const width = Math.max(8, Math.round((value / max) * 100));
    return `${width}%`;
  }

  private maxValue(metric: string): number {
    const data = this.usage();
    if (!data) return 0;
    return data.items.reduce((max, item) => Math.max(max, item.usage[metric] || 0), 0);
  }
}
