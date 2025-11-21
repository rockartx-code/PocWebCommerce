# Arquitectura Serverless de Comercio Electrónico en AWS

## Descripción del Proyecto
Esta solución implementa una aplicación web de comercio electrónico completamente serverless sobre AWS. El frontend está construido con **Angular 20** y estilos con **TailwindCSS**, y se distribuye desde **Amazon S3** detrás de **Amazon CloudFront** para entregar contenido estático con baja latencia. El backend se ejecuta en **AWS Lambda** con **Python**, expone APIs REST mediante **Amazon API Gateway** y utiliza **Amazon Cognito** para autenticación basada en **JWT**. La aplicación se integra con **Mercado Pago** para procesar pagos y ofrece un back office seguro para gestión de catálogo, inventario y métricas de ventas.

## Arquitectura General
- **Entrega web**: Bucket S3 para hosting estático, CDN de CloudFront, dominios personalizados y certificados TLS en ACM.
- **Aplicación frontend**: Angular 20 + Tailwind, empaquetada y publicada en S3; consumo de APIs protegidas con JWT; manejo de carrito y checkout hacia API Gateway.
- **Capa API**: API Gateway con recursos para catálogo, carrito, pedidos y pago; integración Lambda proxy en Python con CORS y validación JWT vía Cognito Authorizer.
- **Lógica de negocio en Lambda (Python)**:
  - Gestión de catálogo e inventario.
  - Carrito y creación de órdenes.
  - Integración con Mercado Pago (creación de preferencias de pago, webhooks de notificación).
  - Webhooks para actualizar estados de pago y conciliar ventas.
- **Datos**: Tablas DynamoDB para productos, inventario y órdenes; S3 para evidencias o exportes; CloudWatch Logs/Metrics para observabilidad.
- **Autenticación y autorización**: User Pool de Cognito con grupos (admin/back office y clientes), JWT usados como `Authorization` en API Gateway; Identity Pool opcional para acceso directo a recursos autorizados.
- **Back office**: Aplicación protegida por login de Cognito, con vistas de catálogo, inventario, pedidos y gráficas de ventas; consumo de APIs autenticadas.
- **Seguridad**: OAI para CloudFront ↔ S3, WAF opcional, variables de entorno cifradas con KMS, roles IAM con mínimos privilegios.

## Servicios a Desarrollar
- **Frontend (Angular 20 + Tailwind)**
  - SPA con catálogo navegable, fichas de producto y buscador.
  - Carrito persistente y flujo de checkout integrado con Mercado Pago.
  - Pantallas de login/registro con Cognito Hosted UI o SDK.
  - Sección de back office (solo admins) para CRUD de productos/inventario, visualización de pedidos y dashboards de ventas.
- **APIs (API Gateway + Lambda Python)**
  - `GET /products`, `GET /products/{id}`: catálogo.
  - `POST /cart`, `GET /cart`: carrito.
  - `POST /orders`: creación de orden y preferencia de pago en Mercado Pago.
  - `POST /webhooks/mercadopago`: recepción de notificaciones de pago.
  - `GET /analytics/sales`: métricas agregadas para dashboards del back office.

## Lambdas en Python y API Gateway
La API se modela con un único Lambda Python (`backend/app.py`) que enruta las solicitudes REST expuestas por API Gateway. Cada recurso está definido en `cloudformation/backend.yml` con integración **AWS_PROXY** hacia el handler `app.handler` y CORS abierto para consumo desde el frontend.

### Rutas generadas
| Método | Ruta | Autenticación | Descripción |
| --- | --- | --- | --- |
| GET | `/v1/products` | Cognito (JWT) | Lista productos disponibles. |
| GET | `/v1/products/{id}` | Cognito (JWT) | Detalle de producto. |
| GET | `/v1/cart` | Cognito (JWT) | Recupera el carrito activo. |
| POST | `/v1/cart` | Cognito (JWT) | Crea/actualiza carrito. |
| POST | `/v1/orders` | Cognito (JWT) | Genera orden y preferencia de pago. |
| POST | `/v1/webhooks/mercadopago` | Público | Webhook para notificaciones de pago. |
| GET | `/v1/analytics/sales` | Cognito (JWT) | Métricas de ventas para dashboards. |

### Flujo y arquitectura
1. **API Gateway** define los recursos bajo `/v1` y aplica un authorizer de Cognito para rutas protegidas.
2. Todas las rutas se integran en modo proxy con la función Lambda, que internamente mapea `httpMethod` y `path` a controladores especializados (catálogo, carrito, órdenes, webhooks y analytics).
3. Las respuestas incluyen encabezados CORS básicos y códigos HTTP adecuados (`200`, `201`, `404`, `500`).
4. Las variables de entorno publican los nombres de tablas DynamoDB (`PRODUCTS_TABLE`, `ORDERS_TABLE`, `CARTS_TABLE`, `TRANSACTIONS_TABLE`) listos para reemplazar la lógica mock por operaciones reales.
- **Integración con Mercado Pago**
  - Creación de preferencias, manejo de `init_point` para redirigir al checkout.
  - Validación de firmas/secretos de webhooks; actualización de estados de pago.
  - Almacenamiento de transacciones y conciliación en DynamoDB.
- **Autenticación (Cognito)**
  - User Pool y App Client con OAuth2/OpenID; grupos `admin` y `customer`.
  - API Gateway Authorizer JWT; políticas IAM para limitar operaciones críticas a admins.

## Estructura de Base de Datos (DynamoDB)
- **Productos (`<stack>-products`)**
  - **PK**: `productId` (S).
  - **GSI `CategoryIndex`**: `category` (PK) + `status` (SK) para listar catálogos por categoría/visibilidad.
  - **GSI `SlugIndex`**: `slug` (PK) para búsquedas rápidas por URL amigable.
  - **Atributos sugeridos**: `name`, `description`, `price`, `currency`, `stock`, `images[]`, `tags[]`, `createdAt`, `updatedAt`.

- **Órdenes (`<stack>-orders`)**
  - **PK**: `orderId` (S) con stream habilitado para integración con analytics.
  - **GSI `OrdersByUser`**: `userId` (PK) + `createdAt` (SK) para el historial del cliente.
  - **GSI `OrdersByStatus`**: `status` (PK) + `updatedAt` (SK) para tableros operativos.
  - **Atributos sugeridos**: `items[]` (producto, cantidad, precio), `amount`, `currency`, `shipping`, `paymentPreferenceId`, `paymentStatus`, `userEmail`, `metadata`.

- **Carritos (`<stack>-carts`)**
  - **PK**: `cartId` (S) con atributo `ttl` para expiración automática.
  - **GSI `UserCartIndex`**: `userId` (PK) + `createdAt` (SK) para recuperar el carrito activo del usuario.
  - **Atributos sugeridos**: `items[]`, `totals`, `promoCode`, `expiresAt`, `channel` (web/app).

- **Transacciones de pago (`<stack>-transactions`)**
  - **PK**: `transactionId` (S) alineado con el `payment_id` de Mercado Pago.
  - **GSI `TransactionsByOrder`**: `orderId` (PK) + `createdAt` (SK) para conciliar pagos por orden.
  - **GSI `TransactionsByStatus`**: `status` (PK) + `createdAt` (SK) para monitorear fallas/aprobaciones recientes.
  - **Atributos sugeridos**: `orderId`, `preferenceId`, `status`, `statusDetail`, `amount`, `currency`, `payer`, `notifications[]`, `rawPayload`.

Estas tablas cubren catálogo, carrito, ordenes y conciliación de pagos; permiten consultas por categoría, estado u usuario, soportan dashboards operativos y facilitan la depuración de integraciones con Mercado Pago.

## Flujo de Despliegue
1. Construir el frontend (`ng build --configuration production`) y publicar el artefacto en el bucket S3 del frontend.
2. Empaquetar funciones Lambda en artefactos ZIP y subirlos a un bucket de artefactos.
3. Desplegar las plantillas de CloudFormation en el siguiente orden sugerido: Cognito → Backend/API → Frontend/CDN.
4. Actualizar variables de entorno (keys de Mercado Pago, URLs de webhook) mediante parámetros seguros o AWS Secrets Manager.

## Archivos de CloudFormation
- **`cloudformation/cognito.yml`**: Crea el User Pool, App Client, dominios opcionales, grupos de usuarios y (opcional) Identity Pool para otorgar credenciales federadas al frontend.
- **`cloudformation/backend.yml`**: Define API Gateway (REST), integraciones Lambda en Python, tablas DynamoDB para productos, carritos y órdenes, y permisos IAM mínimos. Incluye un authorizer JWT conectado a Cognito.
- **`cloudformation/frontend.yml`**: Provisiona el bucket S3 para hosting estático, la distribución CloudFront con OAI, políticas de caché y redirección HTTPS, más registros de salida para el dominio/CDN.
- **`cloudformation/analytics.yml`**: Configura un Dashboard de CloudWatch, alarmas básicas y un bucket de logs para auditoría de acceso y ventas. Útil para el back office y monitoreo.

## Consideraciones de Seguridad y Operación
- Mantener secretos (tokens de Mercado Pago, variables de webhook) en Secrets Manager o Parameter Store con KMS.
- Activar WAF y Shield Advanced si se requieren controles anti-DDoS y filtrado adicional.
- Monitorear latencia/errores con CloudWatch; activar logs detallados y métricas personalizadas en Lambda/API Gateway.
- Automatizar despliegues con pipelines (CodePipeline, GitHub Actions) que invoquen las plantillas de CloudFormation y pruebas automatizadas.

## Desarrollo Local y Pruebas
- Simular APIs con `sam local start-api` o `serverless invoke local` para probar las funciones Python.
- Usar el SDK de Mercado Pago en modo sandbox durante el desarrollo.
- Ejecutar pruebas unitarias de Lambdas con `pytest` y pruebas E2E del frontend con `ng e2e`.

## Módulos de la aplicación web (Angular 20 + Tailwind)
- **Landing** (`frontend/src/app/features/landing`): hero de onboarding que comunica la arquitectura serverless, botones de entrada a catálogo, back office y panel de autenticación, badges de integraciones (API Gateway, Cognito, CloudFront/S3, Mercado Pago).
- **Catálogo** (`frontend/src/app/features/catalog`): grilla de productos con búsqueda reactiva, tarjetas con categoría/stock/precio, acciones para ver detalle y agregar al carrito. Mock local alineado al endpoint `GET /v1/products`.
- **Detalle de producto** (`frontend/src/app/features/product`): ficha completa que ilustra el consumo de `GET /v1/products/{id}` y el disparo de `POST /v1/cart`; incluye tags, precio y bloque de integraciones.
- **Carrito y checkout** (`frontend/src/app/features/cart`): resumen de ítems, edición de cantidades, borrado y cálculo de totales. Simula creación de orden y `paymentPreferenceId` para Mercado Pago vía `POST /v1/orders`.
- **Analytics** (`frontend/src/app/features/analytics`): panel que representa `GET /v1/analytics/sales` con KPIs de ingresos, órdenes, conversión y top productos.
- **Autenticación Cognito** (`frontend/src/app/features/auth`): gestor de Access Token JWT con persistencia en `localStorage`; expone el header `Authorization` para ser reutilizado por servicios HTTP.
- **Back office** (`frontend/src/app/features/admin`): formulario CRUD simulado de catálogo/inventario protegido para admins; punto de partida para enlazar a endpoints seguros de catálogo, pedidos y conciliación de pagos.
- **Servicios compartidos** (`frontend/src/app/shared`): `CatalogService`, `CartService`, `AuthService` y `AnalyticsService` modelan el consumo de la API serverless, estados de carrito y token Cognito.

## Licencia
Este proyecto puede adaptarse según las políticas internas de tu organización. Asegúrate de revisar licencias de dependencias externas (Angular, Tailwind, SDKs de Mercado Pago).
