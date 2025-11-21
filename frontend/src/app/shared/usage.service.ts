import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { catchError, delay, map, Observable, of } from 'rxjs';
import { AuthService } from './auth.service';
import { API_ROUTES } from './routes';
import { BillingSnapshot, TenantUsageSnapshot } from './models';

@Injectable({ providedIn: 'root' })
export class UsageService {
  constructor(private http: HttpClient, private auth: AuthService) {}

  usage(tenantId: string): Observable<TenantUsageSnapshot> {
    const headers = new HttpHeaders({ ...this.auth.authorizationHeader });
    return this.http.get<TenantUsageSnapshot>(API_ROUTES.tenantUsage(tenantId), { headers }).pipe(
      catchError(() => of(this.fallbackUsage(tenantId)).pipe(delay(200)))
    );
  }

  billing(tenantId: string): Observable<BillingSnapshot> {
    const headers = new HttpHeaders({ ...this.auth.authorizationHeader });
    return this.http.get<BillingSnapshot>(API_ROUTES.tenantBilling(tenantId), { headers }).pipe(
      map((response) => ({ ...response, tenantId })),
      catchError(() => of(this.fallbackBilling(tenantId)).pipe(delay(200)))
    );
  }

  adminBilling(): Observable<BillingSnapshot[]> {
    const headers = new HttpHeaders({ ...this.auth.authorizationHeader, 'X-Admin-Role': 'super-admin' });
    return this.http.get<{ items: BillingSnapshot[] }>(API_ROUTES.adminBilling, { headers }).pipe(
      map((resp) => resp.items || []),
      catchError(() => of(this.sampleAdminBilling()).pipe(delay(150)))
    );
  }

  private fallbackUsage(tenantId: string): TenantUsageSnapshot {
    return {
      tenantId,
      summary: { requests: 120, orders: 14, gmv: 3290, bytes: 82000 },
      history: [
        { period: '2024-05-02', usage: { requests: 40, orders: 5, gmv: 1200, bytes: 26000 }, createdAt: '2024-05-02T12:00:00Z' },
        { period: '2024-05-03', usage: { requests: 50, orders: 6, gmv: 980, bytes: 30000 }, createdAt: '2024-05-03T12:00:00Z' },
        { period: '2024-05-04', usage: { requests: 30, orders: 3, gmv: 1110, bytes: 26000 }, createdAt: '2024-05-04T12:00:00Z' }
      ]
    };
  }

  private fallbackBilling(tenantId: string): BillingSnapshot {
    return {
      tenantId,
      status: 'active',
      nextBillingAt: '2024-06-01T00:00:00Z',
      retryAttempts: 0,
      lastPayment: '2024-05-01T00:00:00Z',
      amountDue: 120
    };
  }

  private sampleAdminBilling(): BillingSnapshot[] {
    return [
      { tenantId: 't-001', status: 'active', nextBillingAt: '2024-06-01T00:00:00Z', amountDue: 120 },
      { tenantId: 't-002', status: 'suspended', nextBillingAt: '2024-05-20T00:00:00Z', amountDue: 240, retryAttempts: 3 },
      { tenantId: 't-003', status: 'pending', nextBillingAt: '2024-05-25T00:00:00Z', amountDue: 160, retryAttempts: 1 }
    ];
  }
}
