# Usuarios de prueba

Estos accesos rápidos permiten probar el flujo de autenticación y autorización en los entornos locales o de demo.

## Super admin (cross-tenant)
- **Usuario**: `superadmin@poc-web-commerce.test`
- **Contraseña**: `SuperAdmin!123`
- **Claims sugeridos**:
  - `role`: `super_admin`
  - `tenantId`: `platform` (permite operar sobre cualquier tenant vía rutas `/v1/{tenantId}/...`)

## Admin de tienda
- **Usuario**: `admin@demo-tenant.test`
- **Contraseña**: `AdminDemo!123`
- **Claims sugeridos**:
  - `role`: `admin`
  - `tenantId`: `t-demo`

## Cliente
- **Usuario**: `cliente@demo-tenant.test`
- **Contraseña**: `ClienteDemo!123`
- **Claims sugeridos**:
  - `role`: `customer`
  - `tenantId`: `t-demo`
