import { Injectable } from '@angular/core';
import { delay, Observable, of } from 'rxjs';
import { AuthService } from './auth.service';
import { Product } from './models';

@Injectable({ providedIn: 'root' })
export class CatalogService {
  private readonly tenantAssetPrefix: string;
  private readonly products: Product[];

  constructor(private auth: AuthService) {
    this.tenantAssetPrefix = this.auth.assetPrefix('assets/products');
    this.products = [
      {
        id: 'p-001',
        name: 'Cámara 4K Serverless',
        description: 'Equipo IoT optimizado para subir evidencia a S3 con eventos en EventBridge.',
        price: 499,
        currency: 'USD',
        stock: 23,
        category: 'Electrónica',
        tags: ['4K', 'IoT', 'S3'],
        images: [this.buildImagePath('camara-4k.jpg')]
      },
      {
        id: 'p-002',
        name: 'Terminal POS Integrada',
        description: 'Compatible con Mercado Pago, expone webhooks y recibe confirmación de pagos.',
        price: 259,
        currency: 'USD',
        stock: 12,
        category: 'Pagos',
        tags: ['POS', 'MercadoPago'],
        images: [this.buildImagePath('terminal-pos.jpg')]
      },
      {
        id: 'p-003',
        name: 'Kit Dev Angular + Tailwind',
        description: 'Stack frontend para catálogos headless, con componentes reutilizables.',
        price: 129,
        currency: 'USD',
        stock: 52,
        category: 'Software',
        tags: ['Angular', 'Tailwind'],
        images: [this.buildImagePath('kit-angular-tailwind.jpg')]
      }
    ];
  }

  private buildImagePath(fileName: string): string {
    return `${this.tenantAssetPrefix}/${fileName}`;
  }

  list(search?: string): Observable<Product[]> {
    if (!search) {
      return of(this.products).pipe(delay(300));
    }
    const term = search.toLowerCase();
    const filtered = this.products.filter((p) =>
      `${p.name} ${p.description} ${p.category} ${p.tags.join(' ')}`.toLowerCase().includes(term)
    );
    return of(filtered).pipe(delay(150));
  }

  getById(id: string): Observable<Product | undefined> {
    return of(this.products.find((p) => p.id === id)).pipe(delay(150));
  }
}
