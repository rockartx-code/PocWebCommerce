export const API_ROUTES = {
  tenants: '/v1/tenants',
  tenantUsers: (tenantId: string) => `/v1/tenants/${tenantId}/users`,
  subscriptionCheckout: (tenantId: string) => `/v1/${tenantId}/subscriptions/checkout`,
  products: (tenantId: string) => `/v1/${tenantId}/products`,
  productById: (tenantId: string, id: string) => `/v1/${tenantId}/products/${id}`,
  cart: (tenantId: string) => `/v1/${tenantId}/cart`,
  orders: (tenantId: string) => `/v1/${tenantId}/orders`,
  analytics: (tenantId: string) => `/v1/${tenantId}/analytics/sales`,
  tenantUsage: (tenantId: string) => `/v1/${tenantId}/usage`,
  tenantBilling: (tenantId: string) => `/v1/${tenantId}/billing`,
  mercadopagoWebhook: (tenantId: string) => `/v1/${tenantId}/webhooks/mercadopago`,
  adminUsage: '/v1/admin/tenants/usage',
  adminUsageExport: '/v1/admin/tenants/usage/export',
  adminBilling: '/v1/admin/tenants/billing'
};

export const ROUTES_REQUIRING_TENANT = new Set([
  API_ROUTES.products,
  API_ROUTES.cart,
  API_ROUTES.orders,
  API_ROUTES.analytics,
  API_ROUTES.tenantUsage,
  API_ROUTES.tenantBilling
]);
