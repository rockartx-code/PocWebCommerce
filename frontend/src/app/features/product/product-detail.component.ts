import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { CatalogService } from '../../shared/catalog.service';
import { CartService } from '../../shared/cart.service';
import { Product } from '../../shared/models';

@Component({
  selector: 'app-product-detail',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <section *ngIf="product()" class="grid md:grid-cols-2 gap-8">
      <img [src]="product()!.images[0]" alt="{{ product()!.name }}" class="rounded-2xl border border-slate-800" />
      <div class="space-y-4">
        <div>
          <p class="text-xs uppercase text-indigo-300">{{ product()!.category }}</p>
          <h2 class="text-3xl font-semibold">{{ product()!.name }}</h2>
        </div>
        <p class="text-slate-200">{{ product()!.description }}</p>
        <div class="flex gap-2 text-xs text-indigo-200">
          <span *ngFor="let tag of product()!.tags" class="px-2 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/30">
            {{ tag }}
          </span>
        </div>
        <div class="text-3xl font-bold">{{ product()!.price | currency : product()!.currency }}</div>
        <div class="flex items-center gap-3">
          <button class="px-4 py-2 rounded-lg bg-indigo-500 hover:bg-indigo-400" (click)="addToCart()">Agregar al carrito</button>
          <a routerLink="/catalog" class="text-sm text-slate-300 underline">Volver al catálogo</a>
        </div>
        <div class="border border-slate-800 rounded-xl p-4 bg-slate-900/60 text-sm text-slate-300">
          <p class="font-semibold text-slate-100 mb-2">Integraciones de la ficha</p>
          <ul class="list-disc ml-4 space-y-1">
            <li>GET /v1/products/{id} protegido con JWT Cognito</li>
            <li>Eventos de tracking para analytics y funnels</li>
            <li>Botón Agregar dispara POST /v1/cart</li>
          </ul>
        </div>
      </div>
    </section>
  `
})
export class ProductDetailComponent implements OnInit {
  product = signal<Product | undefined>(undefined);

  constructor(
    private readonly route: ActivatedRoute,
    private readonly catalog: CatalogService,
    private readonly cart: CartService
  ) {}

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.catalog.getById(id).subscribe((product) => this.product.set(product));
    }
  }

  addToCart() {
    const value = this.product();
    if (value) {
      this.cart.add(value);
    }
  }
}
