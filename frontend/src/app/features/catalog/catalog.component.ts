import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { CatalogService } from '../../shared/catalog.service';
import { CartService } from '../../shared/cart.service';
import { Product } from '../../shared/models';

@Component({
  selector: 'app-catalog',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <section class="space-y-4">
      <div class="flex flex-col md:flex-row md:items-center gap-3 justify-between">
        <div>
          <p class="text-xs uppercase tracking-[0.3rem] text-indigo-300">Catálogo</p>
          <h2 class="text-2xl font-semibold">Productos publicados</h2>
          <p class="text-sm text-slate-400">Resultados conectados a /v1/products (mock local).</p>
        </div>
        <input
          [(ngModel)]="search"
          (ngModelChange)="fetch()"
          type="search"
          placeholder="Buscar por nombre, categoría o tag"
          class="px-4 py-2 rounded-lg bg-slate-900/50 border border-slate-800 focus:border-indigo-400 focus:outline-none"
        />
      </div>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <article *ngFor="let product of products()" class="border border-slate-800 rounded-xl bg-slate-900/40 p-4 space-y-3">
          <img [src]="product.images[0]" alt="{{ product.name }}" class="rounded-lg h-36 w-full object-cover" />
          <div class="flex items-start justify-between gap-3">
            <div>
              <p class="text-xs uppercase text-indigo-300">{{ product.category }}</p>
              <h3 class="text-lg font-semibold">{{ product.name }}</h3>
            </div>
            <span class="text-sm text-slate-400">Stock: {{ product.stock }}</span>
          </div>
          <p class="text-sm text-slate-300">{{ product.description }}</p>
          <div class="flex gap-2 text-xs text-indigo-200">
            <span *ngFor="let tag of product.tags" class="px-2 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/30">
              {{ tag }}
            </span>
          </div>
          <div class="flex items-center justify-between">
            <div class="text-xl font-bold">{{ product.price | currency : product.currency }}</div>
            <div class="flex gap-2">
              <button class="px-3 py-2 rounded-lg bg-slate-800 text-sm hover:bg-slate-700" [routerLink]="['/product', product.id]">
                Ver ficha
              </button>
              <button class="px-3 py-2 rounded-lg bg-indigo-500 text-sm text-white hover:bg-indigo-400" (click)="addToCart(product)">
                Agregar
              </button>
            </div>
          </div>
        </article>
      </div>
    </section>
  `
})
export class CatalogComponent implements OnInit {
  products = signal<Product[]>([]);
  search = '';

  constructor(private readonly catalog: CatalogService, private readonly cart: CartService) {}

  ngOnInit(): void {
    this.fetch();
  }

  fetch() {
    this.catalog.list(this.search).subscribe((items) => this.products.set(items));
  }

  addToCart(product: Product) {
    this.cart.add(product);
  }
}
