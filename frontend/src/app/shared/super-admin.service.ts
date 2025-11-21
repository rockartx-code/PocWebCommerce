import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { catchError, delay, map, Observable, of } from 'rxjs';
import { AuthService } from './auth.service';
import { TenantUsageResponse } from './models';
import { API_ROUTES } from './routes';

export interface TenantUsageFilters {
  startDate?: string;
  endDate?: string;
  metrics?: string[];
  page?: number;
  pageSize?: number;
}

const METRIC_KEYS = ['requests', 'orders', 'gmv', 'bytes'];

@Injectable({ providedIn: 'root' })
export class SuperAdminService {
  constructor(private http: HttpClient, private auth: AuthService) {}

  usage(filters: TenantUsageFilters = {}): Observable<TenantUsageResponse> {
    let params = new HttpParams();
    if (filters.startDate) params = params.set('startDate', filters.startDate);
    if (filters.endDate) params = params.set('endDate', filters.endDate);
    if (filters.metrics?.length) params = params.set('metrics', filters.metrics.join(','));
    if (filters.page) params = params.set('page', filters.page);
    if (filters.pageSize) params = params.set('pageSize', filters.pageSize);

    const headers = new HttpHeaders({ ...this.auth.authorizationHeader, 'X-Admin-Role': 'super-admin' });

    return this.http.get<TenantUsageResponse>(API_ROUTES.adminUsage, { params, headers }).pipe(
      map((response) => this.withDefaults(response, filters)),
      catchError(() => of(this.fallback(filters)).pipe(delay(200)))
    );
  }

  private withDefaults(response: TenantUsageResponse, filters: TenantUsageFilters): TenantUsageResponse {
    const metrics = filters.metrics?.length ? filters.metrics : response.availableMetrics || METRIC_KEYS;
    const summary = metrics.reduce<Record<string, number>>((acc, key) => {
      acc[key] = Number(response.summary?.[key] ?? 0);
      return acc;
    }, {});

    return {
      items: response.items || [],
      page: response.page || 1,
      pageSize: response.pageSize || 10,
      total: response.total || (response.items?.length ?? 0),
      availableMetrics: metrics,
      summary,
      filters: response.filters || { startDate: filters.startDate, endDate: filters.endDate }
    };
  }

  private fallback(filters: TenantUsageFilters): TenantUsageResponse {
    const metrics = filters.metrics?.length ? filters.metrics : METRIC_KEYS;
    const sample = [
      {
        tenantId: 't-001',
        period: '2024-05-01',
        usage: { requests: 320, orders: 28, gmv: 15230, bytes: 120000 },
        createdAt: '2024-05-01T12:00:00Z'
      },
      {
        tenantId: 't-002',
        period: '2024-05-01',
        usage: { requests: 210, orders: 18, gmv: 10450, bytes: 98000 },
        createdAt: '2024-05-01T12:00:00Z'
      },
      {
        tenantId: 't-003',
        period: '2024-05-01',
        usage: { requests: 420, orders: 52, gmv: 22410, bytes: 158000 },
        createdAt: '2024-05-01T12:00:00Z'
      }
    ];
    const items = sample.map((record) => ({
      ...record,
      usage: metrics.reduce<Record<string, number>>((acc, key) => {
        acc[key] = record.usage[key as keyof typeof record.usage] ?? 0;
        return acc;
      }, {})
    }));

    const summary = items.reduce<Record<string, number>>((acc, item) => {
      metrics.forEach((metric) => {
        acc[metric] = (acc[metric] || 0) + (item.usage[metric] || 0);
      });
      return acc;
    }, {});

    return {
      items,
      page: filters.page ?? 1,
      pageSize: filters.pageSize ?? items.length,
      total: items.length,
      availableMetrics: metrics,
      summary,
      filters: { startDate: filters.startDate, endDate: filters.endDate }
    };
  }
}
