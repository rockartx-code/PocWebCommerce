export const API_ROUTES = {
  products: (tenantId: string) => `/v1/${tenantId}/products`,
  productById: (tenantId: string, id: string) => `/v1/${tenantId}/products/${id}`,
  cart: (tenantId: string) => `/v1/${tenantId}/cart`,
  orders: (tenantId: string) => `/v1/${tenantId}/orders`,
  analytics: (tenantId: string) => `/v1/${tenantId}/analytics/sales`,
  mercadopagoWebhook: (tenantId: string) => `/v1/${tenantId}/webhooks/mercadopago`
};

export const ROUTES_REQUIRING_TENANT = new Set([
  API_ROUTES.products,
  API_ROUTES.cart,
  API_ROUTES.orders,
  API_ROUTES.analytics
]);
