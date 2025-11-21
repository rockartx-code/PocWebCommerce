export interface Product {
  id: string;
  name: string;
  description: string;
  price: number;
  currency: string;
  stock: number;
  category: string;
  tags: string[];
  images: string[];
}

export interface CartItem {
  product: Product;
  quantity: number;
}

export interface OrderPayload {
  tenantId?: string;
  items: CartItem[];
  total: number;
  paymentPreferenceId?: string;
}

export interface AnalyticsSnapshot {
  period: string;
  revenue: number;
  orders: number;
  conversion: number;
  topProducts: { name: string; sales: number }[];
}

export interface TenantUsageRecord {
  tenantId: string;
  period: string;
  usage: Record<string, number>;
  createdAt: string;
}

export interface UsageHistoryItem {
  period: string;
  usage: Record<string, number>;
  createdAt: string;
}

export interface TenantUsageSnapshot {
  tenantId: string;
  summary: Record<string, number>;
  history: UsageHistoryItem[];
}

export interface BillingSnapshot {
  tenantId: string;
  status: string;
  nextBillingAt?: string;
  retryAttempts?: number;
  lastPayment?: string;
  amountDue?: number;
}

export interface TenantUsageResponse {
  items: TenantUsageRecord[];
  page: number;
  pageSize: number;
  total: number;
  availableMetrics: string[];
  summary: Record<string, number>;
  filters: { startDate?: string | null; endDate?: string | null };
}
