import { API_ROUTES, ROUTES_REQUIRING_TENANT } from './routes';

describe('API_ROUTES', () => {
  it('define rutas coherentes con el backend v1', () => {
    expect(API_ROUTES.products('t-001')).toBe('/v1/t-001/products');
    expect(API_ROUTES.productById('t-001', 'abc')).toBe('/v1/t-001/products/abc');
    expect(API_ROUTES.cart('t-001')).toBe('/v1/t-001/cart');
    expect(API_ROUTES.orders('t-001')).toBe('/v1/t-001/orders');
    expect(API_ROUTES.analytics('t-001')).toBe('/v1/t-001/analytics/sales');
    expect(API_ROUTES.mercadopagoWebhook('t-001')).toBe('/v1/t-001/webhooks/mercadopago');
  });

  it('marca las rutas que requieren tenant', () => {
    expect(ROUTES_REQUIRING_TENANT.has(API_ROUTES.products)).toBeTrue();
    expect(ROUTES_REQUIRING_TENANT.has(API_ROUTES.cart)).toBeTrue();
    expect(ROUTES_REQUIRING_TENANT.has(API_ROUTES.orders)).toBeTrue();
    expect(ROUTES_REQUIRING_TENANT.has(API_ROUTES.analytics)).toBeTrue();
    expect(ROUTES_REQUIRING_TENANT.has(API_ROUTES.mercadopagoWebhook)).toBeFalse();
  });
});
