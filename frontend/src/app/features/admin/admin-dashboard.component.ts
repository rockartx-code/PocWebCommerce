import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Product } from '../../shared/models';

@Component({
  selector: 'app-admin-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <section class="space-y-4">
      <div>
        <p class="text-xs uppercase tracking-[0.3rem] text-indigo-300">Back office</p>
        <h2 class="text-2xl font-semibold">Catálogo e inventario</h2>
        <p class="text-sm text-slate-400">CRUD simulado que consumiría endpoints admins seguros.</p>
      </div>
      <div class="grid md:grid-cols-2 gap-4">
        <form (ngSubmit)="save()" class="border border-slate-800 rounded-xl p-4 bg-slate-900/50 space-y-3">
          <div class="flex gap-3">
            <input [(ngModel)]="draft.name" name="name" placeholder="Nombre" class="w-full px-3 py-2 rounded bg-slate-950 border border-slate-800" />
            <input [(ngModel)]="draft.category" name="category" placeholder="Categoría" class="w-full px-3 py-2 rounded bg-slate-950 border border-slate-800" />
          </div>
          <textarea
            [(ngModel)]="draft.description"
            name="description"
            rows="3"
            placeholder="Descripción"
            class="w-full px-3 py-2 rounded bg-slate-950 border border-slate-800"
          ></textarea>
          <div class="flex gap-3">
            <input [(ngModel)]="draft.price" name="price" type="number" placeholder="Precio" class="w-full px-3 py-2 rounded bg-slate-950 border border-slate-800" />
            <input [(ngModel)]="draft.stock" name="stock" type="number" placeholder="Stock" class="w-full px-3 py-2 rounded bg-slate-950 border border-slate-800" />
          </div>
          <button type="submit" class="px-4 py-2 rounded-lg bg-indigo-500 hover:bg-indigo-400">Guardar producto</button>
        </form>
        <div class="border border-slate-800 rounded-xl p-4 bg-slate-900/50 space-y-3">
          <p class="text-sm text-slate-300">Productos actuales</p>
          <div *ngFor="let product of products()" class="border border-slate-800 rounded-lg p-3 text-sm">
            <div class="flex items-center justify-between">
              <div>
                <p class="font-semibold">{{ product.name }}</p>
                <p class="text-slate-400">{{ product.category }}</p>
              </div>
              <div class="text-indigo-200">{{ product.stock }} uds</div>
            </div>
            <p class="text-slate-400 mt-1">{{ product.description }}</p>
          </div>
          <div *ngIf="!products().length" class="text-xs text-slate-500">Sin productos. Agrega uno para comenzar.</div>
        </div>
      </div>
    </section>
  `
})
export class AdminDashboardComponent {
  products = signal<Product[]>([]);
  draft: Product = {
    id: crypto.randomUUID(),
    name: '',
    description: '',
    price: 0,
    currency: 'USD',
    stock: 0,
    category: '',
    tags: [],
    images: ['https://placehold.co/600x400']
  };

  save() {
    this.products.update((items) => [{ ...this.draft, id: crypto.randomUUID() }, ...items]);
    this.draft = {
      id: crypto.randomUUID(),
      name: '',
      description: '',
      price: 0,
      currency: 'USD',
      stock: 0,
      category: '',
      tags: [],
      images: ['https://placehold.co/600x400']
    };
  }
}
