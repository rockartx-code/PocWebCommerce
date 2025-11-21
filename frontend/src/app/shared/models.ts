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
