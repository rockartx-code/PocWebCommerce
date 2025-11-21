import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CartService } from '../../shared/cart.service';
import { CartItem } from '../../shared/models';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-cart',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <section class="space-y-4">
      <div>
        <p class="text-xs uppercase tracking-[0.3rem] text-indigo-300">Carrito y checkout</p>
        <h2 class="text-2xl font-semibold">Resumen de compra</h2>
        <p class="text-sm text-slate-400">Flujo alineado a POST /v1/cart y POST /v1/orders.</p>
      </div>
      <div class="grid md:grid-cols-[2fr,1fr] gap-4">
        <div class="space-y-3">
          <div *ngFor="let item of items" class="border border-slate-800 rounded-xl p-4 bg-slate-900/50 flex justify-between gap-3">
            <div>
              <p class="text-sm text-indigo-200">{{ item.product.category }}</p>
              <p class="text-lg font-semibold">{{ item.product.name }}</p>
              <p class="text-sm text-slate-400">{{ item.product.description }}</p>
              <div class="text-sm text-slate-300">{{ item.product.price | currency : item.product.currency }}</div>
            </div>
            <div class="flex flex-col items-end gap-2">
              <input
                type="number"
                min="1"
                [ngModel]="item.quantity"
                (ngModelChange)="updateQuantity(item.product.id, $event)"
                class="w-20 px-2 py-1 rounded border border-slate-800 bg-slate-900"
              />
              <button class="text-sm text-red-300" (click)="remove(item.product.id)">Eliminar</button>
            </div>
          </div>
          <div *ngIf="!items.length" class="text-sm text-slate-400">Aún no hay productos en el carrito.</div>
        </div>
        <div class="border border-slate-800 rounded-xl p-4 bg-slate-900/50 h-fit space-y-3">
          <p class="text-sm text-slate-300">Totales</p>
          <div class="text-3xl font-bold">{{ total | currency : 'USD' }}</div>
          <p class="text-xs text-slate-400">Incluye simulación de preferencia de pago para Mercado Pago.</p>
          <button class="w-full px-4 py-2 rounded-lg bg-indigo-500 hover:bg-indigo-400" (click)="checkout()">
            Generar preferencia de pago
          </button>
          <div *ngIf="preferenceId" class="text-xs text-indigo-200">
            Preferencia generada: {{ preferenceId }} (enviada a Mercado Pago)
          </div>
        </div>
      </div>
    </section>
  `
})
export class CartComponent implements OnInit, OnDestroy {
  items: CartItem[] = [];
  total = 0;
  preferenceId = '';
  private sub?: Subscription;
  private totalSub?: Subscription;

  constructor(private readonly cart: CartService) {}

  ngOnInit(): void {
    this.sub = this.cart.items$.subscribe((items) => (this.items = items));
    this.totalSub = this.cart.totals().subscribe((total) => (this.total = total));
  }

  ngOnDestroy(): void {
    this.sub?.unsubscribe();
    this.totalSub?.unsubscribe();
  }

  updateQuantity(productId: string, quantity: number) {
    this.cart.updateQuantity(productId, Number(quantity));
  }

  remove(productId: string) {
    this.cart.remove(productId);
  }

  checkout() {
    const payload = this.cart.buildOrderPayload();
    this.preferenceId = payload.paymentPreferenceId ?? '';
  }
}
