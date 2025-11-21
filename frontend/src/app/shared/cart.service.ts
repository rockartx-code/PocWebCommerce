import { Injectable } from '@angular/core';
import { BehaviorSubject, map } from 'rxjs';
import { CartItem, OrderPayload, Product } from './models';

@Injectable({ providedIn: 'root' })
export class CartService {
  private readonly cart$ = new BehaviorSubject<CartItem[]>([]);

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
    const items = this.cart$.value;
    const total = items.reduce((sum, item) => sum + item.quantity * item.product.price, 0);
    return {
      items,
      total,
      paymentPreferenceId: `pref_${Date.now()}`
    };
  }
}
