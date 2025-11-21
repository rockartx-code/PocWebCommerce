import { API_ROUTES, ROUTES_REQUIRING_TENANT } from './routes';

describe('API_ROUTES', () => {
  it('define rutas coherentes con el backend v1', () => {
    expect(API_ROUTES.products).toBe('/v1/products');
    expect(API_ROUTES.productById('abc')).toBe('/v1/products/abc');
    expect(API_ROUTES.cart).toBe('/v1/cart');
    expect(API_ROUTES.orders).toBe('/v1/orders');
    expect(API_ROUTES.analytics).toBe('/v1/analytics/sales');
    expect(API_ROUTES.mercadopagoWebhook).toBe('/v1/webhooks/mercadopago');
  });

  it('marca las rutas que requieren tenant', () => {
    expect(ROUTES_REQUIRING_TENANT.has(API_ROUTES.products)).toBeTrue();
    expect(ROUTES_REQUIRING_TENANT.has(API_ROUTES.cart)).toBeTrue();
    expect(ROUTES_REQUIRING_TENANT.has(API_ROUTES.orders)).toBeTrue();
    expect(ROUTES_REQUIRING_TENANT.has(API_ROUTES.analytics)).toBeTrue();
    expect(ROUTES_REQUIRING_TENANT.has(API_ROUTES.mercadopagoWebhook)).toBeFalse();
  });
});
