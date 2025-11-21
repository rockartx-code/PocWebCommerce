import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { BehaviorSubject, catchError, map, of } from 'rxjs';
import { CartItem, OrderPayload, Product } from './models';
import { API_ROUTES } from './routes';
import { AuthService } from './auth.service';
import { TenantContextService } from './tenant-context.service';

@Injectable({ providedIn: 'root' })
export class CartService {
  private readonly cart$ = new BehaviorSubject<CartItem[]>([]);

  constructor(
    private readonly http: HttpClient,
    private readonly auth: AuthService,
    private readonly tenantContext: TenantContextService
  ) {}

  get items$() {
    return this.cart$.asObservable();
  }

  add(product: Product) {
    const items = [...this.cart$.value];
    const idx = items.findIndex((i) => i.product.id === product.id);
    if (idx >= 0) {
      items[idx] = { ...items[idx], quantity: items[idx].quantity + 1 };
    } else {
      items.push({ product, quantity: 1 });
    }
    this.cart$.next(items);
  }

  remove(productId: string) {
    this.cart$.next(this.cart$.value.filter((i) => i.product.id !== productId));
  }

  updateQuantity(productId: string, quantity: number) {
    this.cart$.next(
      this.cart$.value.map((i) => (i.product.id === productId ? { ...i, quantity: Math.max(1, quantity) } : i))
    );
  }

  clear() {
    this.cart$.next([]);
  }

  totals() {
    return this.cart$.pipe(
      map((items) => items.reduce((sum, item) => sum + item.quantity * item.product.price, 0))
    );
  }

  buildOrderPayload(): OrderPayload {
    const tenantId = this.resolveTenantId();
    const items = this.cart$.value;
    const total = items.reduce((sum, item) => sum + item.quantity * item.product.price, 0);
    return {
      tenantId,
      items,
      total,
      paymentPreferenceId: `pref_${Date.now()}`
    };
  }

  createOrder() {
    const tenantId = this.resolveTenantId();
    const payload = this.buildOrderPayload();
    const headers = new HttpHeaders({ ...this.auth.authorizationHeader, 'X-Tenant-Id': tenantId });
    const params = new HttpParams().set('tenantId', tenantId);
    return this.http.post<{ paymentPreferenceId?: string }>(API_ROUTES.orders(tenantId), payload, { headers, params }).pipe(
      map((res) => res.paymentPreferenceId ?? payload.paymentPreferenceId ?? ''),
      catchError(() => of(payload.paymentPreferenceId ?? ''))
    );
  }

  private resolveTenantId(): string {
    const tenantId = this.tenantContext.tenantId() || this.auth.tenantId;
    if (!tenantId) {
      throw new Error('TenantId no disponible para el carrito');
    }
    return tenantId;
  }
}
