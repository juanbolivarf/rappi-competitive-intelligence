# Cloudflare Browser Rendering - Problemas Conocidos

## Resumen

Cloudflare Browser Rendering fue elegido inicialmente como el backend de scraping para este proyecto. Aunque funciona para algunos casos, encontramos varios problemas que nos llevaron a implementar extracción SSR (Server-Side Rendering) como método principal.

**Recomendación Actual**: Usar modo SSR (por defecto) para Rappi y Uber Eats. Usar modo de datos de prueba para DiDi Food.

---

## Problema #1: Límite de Neuronas en Plan Gratuito (CRÍTICO)

### Problema
El plan gratuito de Cloudflare tiene un **límite diario de 10,000 neuronas** para extracción con IA. Una vez excedido, todas las solicitudes fallan con errores HTTP 422 hasta el día siguiente.

### Mensaje de Error
```
HTTP 422 from Cloudflare: {"success":false,"errors":[{"message":"AI error: AiError: 4006:
you have used up your daily free allocation of 10,000 neurons, please upgrade to
Cloudflare's Workers Paid plan if you would like to continue using AI features"}]}
```

### Impacto
- Una sola extracción de página puede consumir 500-2000 neuronas
- Con 15 direcciones × 3 plataformas = 45 páginas = **~45,000 neuronas mínimo**
- **El plan gratuito se agota después de ~5-10 scrapes por día**

### Solución Requerida
- Actualizar al plan de pago de Cloudflare Workers ($5/mes + uso)
- O usar extracción SSR (GRATIS, sin límites)

---

## Problema #2: Limitación de Tasa (Errores 429)

### Problema
Cloudflare impone límites estrictos de tasa en las llamadas a la API de Browser Rendering. Al scrapear múltiples direcciones/productos, frecuentemente recibimos errores `429 Too Many Requests`.

### Síntomas
```
Error: Request rate limited (429)
Cloudflare Browser Rendering: Rate limit exceeded
```

### Mitigaciones Intentadas
- Aumentar `SCRAPE_DELAY_SECONDS` a 8+ segundos
- Reducir tamaños de lote
- Implementar backoff exponencial

### Resultado
Parcialmente efectivo. Aún alcanza límites en scrapes completos (15+ direcciones).

---

## Problema #3: Errores de Timeout

### Problema
Algunas páginas tardan más que el timeout de la API en renderizar completamente, especialmente páginas con JavaScript pesado o contenido cargado de forma diferida.

### Síntomas
```
Error: Request timed out after 60000ms
Page load timeout exceeded
```

### Mitigaciones Intentadas
- Aumentar `REQUEST_TIMEOUT` a 60+ segundos
- Agregar lógica de espera por selector

### Resultado
Inconsistente. Algunas páginas aún dan timeout incluso con límites extendidos.

---

## Problema #4: Detección de Bots

### Problema
Las plataformas de delivery implementan detección de bots que identifica la huella digital del navegador headless de Cloudflare.

### Síntomas
- Respuestas vacías
- Desafíos de captcha
- Redirecciones a páginas de error
- Datos faltantes en respuestas aparentemente exitosas

### Plataformas Afectadas
- **DiDi Food**: Detección más agresiva
- **Uber Eats**: Detección ocasional
- **Rappi**: Menor detección

### Resultado
No se puede evadir de forma confiable. Requiere randomización de huella digital más sofisticada.

---

## Problema #5: Muro de Login de DiDi Food

### Problema
DiDi Food requiere autenticación de usuario para ver precios de menú, tarifas de envío y tiempos estimados. Esto no es una limitación técnica de Cloudflare sino una decisión de diseño de la plataforma.

### Síntomas
- Listados de restaurantes visibles pero sin precios
- Mensajes de "Inicia sesión para ver precios"
- Datos de carrito/checkout vacíos

### Mitigaciones Intentadas
- Intentamos cookies de sesión (expiraron rápido)
- Intentamos inyección de token OAuth (bloqueado)
- Investigamos API de app móvil (requiere dispositivo rooteado)

### Resultado
No es posible sin sesión de usuario válida. Ver `DIDI_FOOD_INVESTIGATION.md` para investigación completa.

---

## Problema #6: Costo

### Problema
Cloudflare Browser Rendering consume créditos de API. Para inteligencia competitiva que requiere scrapes frecuentes, los costos se acumulan.

### Cálculo
- ~$0.01-0.02 por renderizado de página
- 15 direcciones × 4 productos × 3 plataformas = 180 renderizados
- Scrape completo = ~$2-4
- Monitoreo diario = ~$60-120/mes

### Resultado
La extracción SSR es gratuita y funciona para Rappi y Uber Eats.

---

## Problema #7: Inconsistencias en Renderizado de JavaScript

### Problema
El contenido dinámico no siempre se renderiza completamente. Precios, tarifas o tiempos a veces faltan incluso en cargas de página exitosas.

### Síntomas
- `product_price_mxn: null` en scrapes aparentemente exitosos
- Extracción de datos parcial
- Resultados inconsistentes entre ejecuciones

### Causa
- Carga diferida no activada
- Observers de intersección no disparados
- Llamadas a API no completadas antes de la captura

### Resultado
La extracción SSR obtiene datos directamente de HTML/JSON, evitando problemas de renderizado.

---

## Comparación: Cloudflare vs SSR

| Aspecto | Cloudflare | SSR |
|---------|------------|-----|
| Costo | ~$0.01/página | GRATIS |
| Velocidad | 5-15 seg/página | 1-2 seg/página |
| Confiabilidad | ~70-80% | ~90-95% |
| Límites de Tasa | Estrictos | Flexibles |
| DiDi Food | Bloqueado | Bloqueado |
| Detección de Bots | A veces detectado | Raramente detectado |
| JavaScript | Renderizado completo | No necesario |

---

## Enfoques Alternativos de Scraping

Dadas las limitaciones del plan gratuito de Cloudflare, aquí hay enfoques alternativos para desarrollo futuro:

### 1. Scraping Basado en Agente IA

Usar un agente IA (como Claude o GPT-4) con capacidades de uso de computadora para navegar sitios web como un usuario humano.

**Ventajas:**
- Puede manejar contenido dinámico y JavaScript
- Se adapta a cambios de UI automáticamente
- Puede resolver CAPTCHAs con interacción tipo humano
- Sin límites de tasa de APIs de scraping

**Desventajas:**
- Mayor latencia (el agente piensa antes de cada acción)
- Más costoso por página ($0.05-0.20 por página)
- Requiere ingeniería de prompts cuidadosa

**Implementación:**
```python
# Ejemplo con Claude Computer Use
from anthropic import Anthropic

client = Anthropic()
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    tools=[{"type": "computer_20241022", "display_width": 1024, "display_height": 768}],
    messages=[{
        "role": "user",
        "content": "Ve a rappi.com.mx, busca McDonald's cerca de Providencia, "
                   "y extrae el precio del Big Mac y la tarifa de envío."
    }]
)
```

### 2. Browserless.io o Servicios Similares

Servicios de navegador en la nube con mejores límites de tasa y precios.

**Opciones:**
- Browserless.io (~$0.01/página)
- ScrapingBee (~$0.001/página)
- Bright Data (~$0.002/página)

### 3. Playwright con Proxies Residenciales

Ejecutar tu propio navegador Playwright con IPs residenciales rotativas para evitar detección.

**Ventajas:**
- Control total sobre comportamiento del navegador
- Sin límites de neuronas/API
- Costo único de proxy

**Desventajas:**
- Requiere suscripción de proxy (~$15-50/mes)
- Más infraestructura que mantener

### 4. APIs Oficiales (Donde Estén Disponibles)

Algunas plataformas ofrecen APIs de socios/afiliados:
- **Rappi**: API de Socios (requiere relación comercial)
- **Uber Eats**: API de Afiliados (datos limitados)
- **DiDi Food**: Sin API pública

### 5. Enfoque Híbrido (Recomendado)

Combinar múltiples métodos para resiliencia:
1. **Primario**: Extracción SSR (GRATIS) para Rappi + Uber Eats
2. **Respaldo**: Playwright con proxy para extracciones fallidas
3. **DiDi Food**: Agente IA o recolección manual
4. **Pruebas**: Datos sintéticos para desarrollo

---

## Conclusión

La extracción SSR es el enfoque recomendado para este proyecto:
- **Rappi**: SSR funciona bien, extrae todos los datos
- **Uber Eats**: SSR + Playwright para datos completos
- **DiDi Food**: Usar datos de prueba sintéticos (muro de login bloquea todos los métodos automatizados)

Cloudflare Browser Rendering **no se recomienda** para uso en producción debido a:
1. Límite de neuronas del plan gratuito (10,000/día) se agota rápido
2. Plan de pago añade costos continuos
3. Extracción SSR es más rápida y gratuita

Para escalamiento futuro, considerar scraping basado en agente IA o un enfoque híbrido con proxies residenciales.
