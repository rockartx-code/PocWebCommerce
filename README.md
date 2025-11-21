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
- **Datos**: Tablas DynamoDB para productos, inventario por ubicación, carritos, órdenes, ítems de orden y pagos; S3 para evidencias o exportes; CloudWatch Logs/Metrics para observabilidad.
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
- **Integración con Mercado Pago**
  - Creación de preferencias, manejo de `init_point` para redirigir al checkout.
  - Validación de firmas/secretos de webhooks; actualización de estados de pago.
  - Almacenamiento de transacciones y conciliación en DynamoDB.
- **Autenticación (Cognito)**
  - User Pool y App Client con OAuth2/OpenID; grupos `admin` y `customer`.
  - API Gateway Authorizer JWT; políticas IAM para limitar operaciones críticas a admins.

## Estructura de Base de Datos (DynamoDB)
- **ProductsTable** (`productId` PK)
  - Atributos clave: `category` (GSI `category-index` para filtros por categoría), `price`, `status`, `slug`.
  - Uso: catálogo público, detalle de producto y datos de pricing.
- **InventoryTable** (`productId` PK, `locationId` SK)
  - Atributos clave: `stock`, `safetyStock`, `reserved`.
  - Uso: control de inventario por ubicación (bodega/tienda) y para reservar/unreservar unidades durante el checkout.
- **CartsTable** (`userId` PK, `itemId` SK, TTL `ttl`)
  - Atributos clave: `productId`, `quantity`, `priceSnapshot`.
  - Uso: items del carrito por usuario autenticado o sesión; TTL permite expirar carritos inactivos.
- **OrdersTable** (`orderId` PK)
  - Atributos clave: `userId`, `status`, `paymentStatus`, `total`, `createdAt`.
  - GSI `userId-createdAt-index` para listar órdenes de un cliente en el back office o el frontend.
- **OrderItemsTable** (`orderId` PK, `itemId` SK)
  - Atributos clave: `productId`, `quantity`, `unitPrice`, `subtotal`.
  - GSI `productId-index` para analítica de ventas por producto y conciliación de inventario.
- **PaymentsTable** (`paymentId` PK)
  - Atributos clave: `orderId`, `status`, `mpPreferenceId`, `mpPaymentType`, `amount`, `capturedAt`.
  - GSI `orderId-index` para resolver rápidamente el estado de pago de una orden y recibir webhooks de Mercado Pago.

## Flujo de Despliegue
1. Construir el frontend (`ng build --configuration production`) y publicar el artefacto en el bucket S3 del frontend.
2. Empaquetar funciones Lambda en artefactos ZIP y subirlos a un bucket de artefactos.
3. Desplegar las plantillas de CloudFormation en el siguiente orden sugerido: Cognito → Backend/API → Frontend/CDN.
4. Actualizar variables de entorno (keys de Mercado Pago, URLs de webhook) mediante parámetros seguros o AWS Secrets Manager.

## Archivos de CloudFormation
- **`cloudformation/cognito.yml`**: Crea el User Pool, App Client, dominios opcionales, grupos de usuarios y (opcional) Identity Pool para otorgar credenciales federadas al frontend.
- **`cloudformation/backend.yml`**: Define API Gateway (REST), integraciones Lambda en Python, tablas DynamoDB para productos, inventario, carritos, órdenes, ítems de orden y pagos, y permisos IAM mínimos. Incluye un authorizer JWT conectado a Cognito.
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

## Licencia
Este proyecto puede adaptarse según las políticas internas de tu organización. Asegúrate de revisar licencias de dependencias externas (Angular, Tailwind, SDKs de Mercado Pago).
