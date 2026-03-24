# Reporte de Investigación de DiDi Food

## Resumen

DiDi Food presenta desafíos técnicos significativos para la recolección de datos de inteligencia competitiva. A diferencia de Rappi y Uber Eats, que exponen datos de menú y precios a través de HTML renderizado del lado del servidor (SSR), DiDi Food implementa múltiples capas de protección que hacen la extracción automatizada de datos extremadamente difícil.

**Estado Final**: El scraping de DiDi Food actualmente no es factible sin:
- Un dispositivo Android rooteado, O
- Un dispositivo iOS con jailbreak, O
- Recolección manual de datos

Para el MVP, recomendamos usar datos sintéticos para DiDi Food (disponible con la bandera `--test-data`) mientras se recolectan datos en tiempo real de Rappi y Uber Eats.

---

## Cronología de la Investigación

### Fase 1: Enfoque Basado en Web

**Intento**: Acceder al sitio web de DiDi Food directamente mediante extracción SSR (igual que Rappi/Uber Eats)

**Hallazgo**: El sitio web de DiDi Food (`https://www.didifood.com/`) tiene un **muro de login** - todos los datos de menú y precios están ocultos tras autenticación. El sitio muestra:
- Listados de restaurantes (solo nombres e imágenes)
- Sin precios
- Sin tarifas de envío
- Sin tiempos estimados
- Sin artículos del menú

**Bloqueador**: Autenticación requerida. No se pueden extraer datos de páginas web públicas.

---

### Fase 2: Intercepción de API de App Móvil

La app móvil contiene todos los datos que necesitamos. El plan era interceptar tráfico HTTPS para hacer ingeniería inversa de la API.

#### 2.1 Configuración de mitmproxy

**Pasos completados**:
1. Instalamos mitmproxy vía pip
2. Iniciamos servidor proxy en `192.168.0.113:8080`
3. Capturamos tráfico HTTP exitosamente

#### 2.2 Intento con iPhone

**Dispositivo**: iPhone (iOS)

**Pasos completados**:
1. Configuramos proxy WiFi para apuntar a mitmproxy
2. Instalamos certificado CA de mitmproxy
3. Abrimos app de DiDi Food

**Resultado**: El tráfico capturado mostró solo handshakes TLS encriptados

**Bloqueador**: **SSL Certificate Pinning**
Las apps de iOS pueden verificar que los certificados del servidor coincidan con certificados conocidos embebidos en la app, bloqueando la intercepción del proxy. Evadir esto requiere:
- Dispositivo con jailbreak con SSL Kill Switch 2
- Frida con scripts de bypass SSL (requiere jailbreak)

---

### Fase 3: Teléfono Android (Sin Root)

**Dispositivo**: Redmi Note 12C (Android, sin root)

#### 3.1 Enfoque con Servidor Frida

**Frida** es un toolkit de instrumentación dinámica que puede engancharse a apps en ejecución y evadir SSL pinning.

**Pasos completados**:
1. Habilitamos depuración USB en el teléfono
2. Conectamos vía ADB (Android Debug Bridge)
3. Descargamos servidor Frida (versión ARM64)
4. Intentamos subir servidor Frida al dispositivo

**Resultado**: `su: inaccessible or not found`

**Bloqueador**: **Acceso root requerido**
El servidor Frida requiere acceso root (superusuario) para engancharse a procesos de apps. Los teléfonos Android de consumo no vienen rooteados por defecto.

#### 3.2 Enfoque con HTTP Toolkit

HTTP Toolkit es una alternativa más amigable que afirma funcionar en algunos dispositivos sin root.

**Pasos completados**:
1. Descargamos e instalamos HTTP Toolkit
2. Conectamos al dispositivo Android vía ADB
3. Configuramos ajustes de proxy

**Resultado**: Los logs mostraron `Root not available, skipping cert injection`

**Bloqueador**: **Acceso root requerido**
La intercepción ADB de HTTP Toolkit también requiere root para inyectar certificados en el almacén de certificados del sistema.

---

### Fase 4: Emulador Android (Rooteado)

Los emuladores Android con imágenes de Google APIs (no Play Store) pueden ejecutarse como root.

#### 4.1 Configuración del Emulador

**Pasos completados**:
1. Descargamos herramientas de línea de comandos del SDK de Android
2. Descargamos OpenJDK 21
3. Instalamos:
   - Paquete `emulator`
   - `platform-tools` (ADB)
   - `system-images;android-30;google_apis;x86_64`
4. Creamos AVD (Android Virtual Device) llamado `didi_test2`
5. Iniciamos emulador con bandera `-writable-system`
6. Confirmamos acceso root vía `adb root`

#### 4.2 Instalación de DiDi Food

**Pasos completados**:
1. Extrajimos APK de DiDi Food del teléfono físico del usuario:
   - APK Base: `base.apk` (132MB)
   - APKs divididos para arquitectura y DPI
2. Instalamos APK en emulador: `adb install didi_food.apk`
3. Instalación exitosa

#### 4.3 Configuración del Servidor Frida

**Pasos completados**:
1. Descargamos servidor Frida para arquitectura x86_64
2. Subimos al emulador: `/data/local/tmp/frida-server`
3. Hicimos ejecutable: `chmod +x`
4. Creamos script de bypass SSL (`ssl_bypass.js`) con:
   - Bypass de TrustManager
   - Bypass de OkHttp3 CertificatePinner
   - Bypass de TrustManagerImpl
   - Bypass de NetworkSecurityConfig

#### 4.4 Problema de Conectividad de Red

**Problema**: La app de DiDi Food no se ejecutaba correctamente

**Diagnóstico**:
- `ping 8.8.8.8` retornaba 100% de pérdida de paquetes
- Gateway interno (10.0.2.2) era alcanzable
- Servidor DNS (10.0.2.3) era alcanzable
- Faltaba ruta por defecto en tabla de enrutamiento
- Agregamos ruta: `ip route add default via 10.0.2.2 dev eth0`

**Bloqueador**: **Configuración de red del emulador**
Incluso después de agregar la ruta por defecto, la conectividad a internet externa falló. Esto parece ser un problema de firewall de Windows o NAT con el stack de red del emulador Android.

**Intentos adicionales**:
- Reiniciamos emulador con `-dns-server 8.8.8.8,8.8.4.4`
- Verificamos reglas de iptables (todas políticas ACCEPT)
- Verificamos modo avión (deshabilitado)

El emulador podía alcanzar su gateway local pero no podía alcanzar internet.

---

## Resumen de Bloqueadores Técnicos

| Enfoque | Bloqueador | Posible Solución |
|---------|------------|------------------|
| Web SSR | Muro de login | N/A - datos no expuestos |
| Proxy iPhone | SSL pinning | Jailbreak + SSL Kill Switch |
| Proxy Android | SSL pinning | Root + Frida |
| HTTP Toolkit | Root requerido | Rootear el dispositivo |
| Emulador Android | Conectividad de red | Depurar firewall/NAT de Windows |

---

## Archivos Creados Durante la Investigación

| Archivo | Propósito |
|---------|-----------|
| `ssl_bypass.js` | Script de Frida para bypass de SSL pinning |
| `didi_capture.flow` | Archivo de captura de mitmproxy (21MB) |
| `didi_emulator_capture.flow` | Intento de captura del emulador |

---

## Próximos Pasos Recomendados

### Opción A: Continuar con DiDi Food (Alto Esfuerzo)

1. **Arreglar red del emulador**
   - Depurar reglas del Firewall de Windows
   - Probar en host Linux o macOS (mejor soporte de emulador)
   - Probar emulador Genymotion (comercial, mejor red)

2. **Alternativa: Dispositivo Android en la nube**
   - Servicios como AWS Device Farm o Firebase Test Lab
   - Imágenes de Android pre-rooteadas disponibles

3. **Alternativa: Rootear dispositivo físico**
   - Teléfonos Android más antiguos son más fáciles de rootear
   - Riesgo: puede brickear dispositivo, anula garantía

### Opción B: Usar Datos Sintéticos (Recomendado para MVP)

El generador de datos sintéticos (`synthetic_data.py`) crea precios realistas de DiDi Food basados en patrones de mercado observados:

- **Multiplicador de precio**: 0.93x (7% más barato que baseline - estrategia de precios agresiva)
- **Tarifas de envío**: Mayor premium periférico (+$18 MXN en zonas de bajos ingresos)
- **Tarifa de servicio**: 8% (la más baja entre plataformas)
- **Probabilidad de promo**: 45% (promociones más agresivas)
- **Cobertura**: 82% tasa de disponibilidad (menor cobertura)

Uso:
```bash
python main.py --test-data
```

Esto genera datos para las 3 plataformas con dinámicas competitivas realistas.

### Opción C: Recolección Manual de Datos

Para datos precisos de DiDi Food:
1. Abrir app de DiDi Food en el teléfono
2. Buscar restaurantes objetivo
3. Registrar precios, tarifas y tiempos manualmente
4. Importar al sistema vía CSV

### Opción D: Scraping Basado en Agente IA (Futuro)

Usar un agente IA con capacidades de uso de computadora para navegar la app o sitio web de DiDi Food como un humano.

**Ventajas:**
- Puede autenticarse como usuario real
- Se adapta a cambios de UI
- Puede manejar CAPTCHAs

**Implementación:**
```python
from anthropic import Anthropic

client = Anthropic()
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    tools=[{"type": "computer_20241022", "display_width": 1024, "display_height": 768}],
    messages=[{
        "role": "user",
        "content": "Abre DiDi Food, inicia sesión, busca McDonald's en Providencia "
                   "y extrae el precio del Big Mac y la tarifa de envío."
    }]
)
```

---

## Conclusión

Las medidas de seguridad agresivas de DiDi Food (SSL pinning, muros de login) están diseñadas para proteger sus datos de precios de la recolección de inteligencia competitiva. Aunque técnicamente es posible evadirlas con dispositivos rooteados, el esfuerzo requerido excede el alcance del MVP.

El enfoque de datos sintéticos proporciona dinámicas de mercado realistas para propósitos de análisis y visualización, mientras que el scraping en tiempo real se enfoca en las plataformas accesibles (Rappi y Uber Eats).

Para desarrollo futuro, el scraping basado en agente IA presenta la solución más prometedora ya que puede:
- Autenticarse como usuario real
- Navegar la app de forma dinámica
- Adaptarse a cambios sin modificaciones de código

---

## Referencias

- [Documentación de Frida](https://frida.re/docs/)
- [Técnicas de Bypass de SSL Pinning](https://blog.netspi.com/four-ways-to-bypass-android-ssl-verification-and-certificate-pinning/)
- [Red de Emulador Android](https://developer.android.com/studio/run/emulator-networking)
- [Documentación de mitmproxy](https://docs.mitmproxy.org/)
- [Claude Computer Use](https://docs.anthropic.com/en/docs/computer-use)
