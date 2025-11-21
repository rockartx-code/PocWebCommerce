import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { API_ROUTES } from './routes';

export interface TenantBranding {
  primaryColor: string;
  domain: string;
  logoUrl?: string;
}

export interface TenantCreationPayload {
  name: string;
  industry: string;
  currency: string;
  paymentProvider: string;
  paymentKeys?: Record<string, string>;
  adminEmail: string;
  branding: TenantBranding;
}

export interface TenantUserPayload {
  email: string;
  role: string;
  temporaryPassword?: string;
  displayName?: string;
}

export interface TenantCreationResponse {
  tenant: {
    tenantId: string;
    name: string;
    industry: string;
    status: string;
    preferredCurrency: string;
    paymentProvider: string;
    branding: TenantBranding;
    createdAt: string;
  };
  adminUser: TenantUserPayload & { userId: string; loginUrl: string; temporaryPassword: string };
  urls: {
    storefront: string;
    backoffice: string;
    apiBase: string;
  };
  onboardingToken: string;
}

export interface TenantUserResponse {
  tenantId: string;
  user: TenantUserPayload & { userId: string; status: string; temporaryPassword: string; createdAt: string };
  loginUrl: string;
  support: string;
}

export interface SubscriptionCheckoutResponse {
  tenantId: string;
  subscriptionId: string;
  planId: string;
  checkoutPreference: { id: string; type: string; provider: string };
  status: string;
  nextBillingAt?: string;
}

@Injectable({ providedIn: 'root' })
export class OnboardingService {
  constructor(private http: HttpClient) {}

  createTenant(payload: TenantCreationPayload) {
    return this.http.post<TenantCreationResponse>(API_ROUTES.tenants, payload);
  }

  createTenantUser(tenantId: string, payload: TenantUserPayload) {
    return this.http.post<TenantUserResponse>(API_ROUTES.tenantUsers(tenantId), payload);
  }

  createSubscriptionCheckout(tenantId: string, payload: { planId: string }) {
    return this.http.post<SubscriptionCheckoutResponse>(API_ROUTES.subscriptionCheckout(tenantId), payload);
  }
}
