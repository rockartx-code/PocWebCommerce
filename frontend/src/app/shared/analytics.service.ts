import { Injectable } from '@angular/core';
import { delay, Observable, of } from 'rxjs';
import { AnalyticsSnapshot } from './models';

@Injectable({ providedIn: 'root' })
export class AnalyticsService {
  private readonly snapshot: AnalyticsSnapshot = {
    period: 'Últimos 30 días',
    revenue: 48250,
    orders: 1320,
    conversion: 3.4,
    topProducts: [
      { name: 'Cámara 4K Serverless', sales: 320 },
      { name: 'Kit Dev Angular + Tailwind', sales: 270 },
      { name: 'Terminal POS Integrada', sales: 210 }
    ]
  };

  metrics(): Observable<AnalyticsSnapshot> {
    return of(this.snapshot).pipe(delay(200));
  }
}
