export const API_ROUTES = {
  products: '/v1/products',
  productById: (id: string) => `/v1/products/${id}`,
  cart: '/v1/cart',
  orders: '/v1/orders',
  analytics: '/v1/analytics/sales',
  mercadopagoWebhook: '/v1/webhooks/mercadopago'
};

export const ROUTES_REQUIRING_TENANT = new Set([
  API_ROUTES.products,
  API_ROUTES.cart,
  API_ROUTES.orders,
  API_ROUTES.analytics
]);
