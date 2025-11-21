import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { catchError, delay, map, Observable, of } from 'rxjs';
import { AuthService } from './auth.service';
import { Product } from './models';
import { API_ROUTES } from './routes';
import { TenantContextService } from './tenant-context.service';

@Injectable({ providedIn: 'root' })
export class CatalogService {
  private readonly productsByTenant = new Map<string, Product[]>();

  constructor(
    private auth: AuthService,
    private http: HttpClient,
    private tenantContext: TenantContextService
  ) {}

  private buildImagePath(tenantId: string, fileName: string): string {
    return `https://cdn.poc-web-commerce.example/${tenantId}/assets/products/${fileName}`;
  }

  private resolveTenantId(): string {
    const tenantId = this.tenantContext.tenantId() || this.auth.tenantId;
    if (!tenantId) {
      throw new Error('TenantId no disponible');
    }
    return tenantId;
  }

  private tenantHeaders(tenantId: string): HttpHeaders {
    return new HttpHeaders({ ...this.auth.authorizationHeader, 'X-Tenant-Id': tenantId });
  }

  private tenantParams(tenantId: string, search?: string): HttpParams {
    let params = new HttpParams().set('tenantId', tenantId);
    if (search) {
      params = params.set('search', search);
    }
    return params;
  }

  private bootstrapProducts(tenantId: string): Product[] {
    if (this.productsByTenant.has(tenantId)) {
      return this.productsByTenant.get(tenantId) ?? [];
    }
    const defaults: Product[] = [
      {
        id: `${tenantId}-p-001`,
        name: 'Cámara 4K Serverless',
        description: 'Equipo IoT optimizado para subir evidencia a S3 con eventos en EventBridge.',
        price: 499,
        currency: 'USD',
        stock: 23,
        category: 'Electrónica',
        tags: ['4K', 'IoT', 'S3'],
        images: [this.buildImagePath(tenantId, 'camara-4k.jpg')]
      },
      {
        id: `${tenantId}-p-002`,
        name: 'Terminal POS Integrada',
        description: 'Compatible con Mercado Pago, expone webhooks y recibe confirmación de pagos.',
        price: 259,
        currency: 'USD',
        stock: 12,
        category: 'Pagos',
        tags: ['POS', 'MercadoPago'],
        images: [this.buildImagePath(tenantId, 'terminal-pos.jpg')]
      },
      {
        id: `${tenantId}-p-003`,
        name: 'Kit Dev Angular + Tailwind',
        description: 'Stack frontend para catálogos headless, con componentes reutilizables.',
        price: 129,
        currency: 'USD',
        stock: 52,
        category: 'Software',
        tags: ['Angular', 'Tailwind'],
        images: [this.buildImagePath(tenantId, 'kit-angular-tailwind.jpg')]
      }
    ];
    this.productsByTenant.set(tenantId, defaults);
    return defaults;
  }

  private filterProducts(products: Product[], search?: string): Product[] {
    if (!search) {
      return products;
    }
    const term = search.toLowerCase();
    return products.filter((p) =>
      `${p.name} ${p.description} ${p.category} ${p.tags.join(' ')}`.toLowerCase().includes(term)
    );
  }

  list(search?: string): Observable<Product[]> {
    const tenantId = this.resolveTenantId();
    const headers = this.tenantHeaders(tenantId);
    const params = this.tenantParams(tenantId, search);
    return this.http.get<{ items?: Product[] }>(API_ROUTES.products(tenantId), { headers, params }).pipe(
      map((response) => this.filterProducts(this.normalizeProducts(response.items ?? [], tenantId), search)),
      catchError(() => of(this.filterProducts(this.bootstrapProducts(tenantId), search)).pipe(delay(150)))
    );
  }

  getById(id: string): Observable<Product | undefined> {
    const tenantId = this.resolveTenantId();
    const headers = this.tenantHeaders(tenantId);
    const params = this.tenantParams(tenantId);
    return this.http.get<Product>(API_ROUTES.productById(tenantId, id), { headers, params }).pipe(
      map((product) => this.normalizeProduct(product, tenantId)),
      catchError(() => of(this.bootstrapProducts(tenantId).find((p) => p.id === id)).pipe(delay(150)))
    );
  }

  private normalizeProducts(products: Product[], tenantId: string): Product[] {
    return products.map((product) => this.normalizeProduct(product, tenantId));
  }

  private normalizeProduct(product: Product, tenantId: string): Product {
    const id = product.id ?? product['productId'] ?? `${tenantId}-${crypto.randomUUID()}`;
    const images = product.images?.length ? product.images : [this.buildImagePath(tenantId, `${id}.jpg`)];
    return { ...product, id, images };
  }
}
