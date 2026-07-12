# Smoke Test — Certificación de Entorno Productivo (HU22)

**Fecha de ejecución:** 2026-07-12
**Ejecutado por:** Isaac Camilo Giraldo Gómez — Equipo 326
**Entorno:** Producción (Render + Supabase)

---

## URLs verificadas

| Servicio | URL | Estado |
|---|---|---|
| Backend API | https://vitalriskia.onrender.com | ✅ |
| Frontend Dashboard | https://vitalriskia-frontend.onrender.com | ✅ |
| Swagger / Documentación | https://vitalriskia.onrender.com/docs | ✅ |

---

## Checklist — Happy Path (criterios HU22)

### Infraestructura
- [x] `GET /api/v1/health/` retorna `{"status": "OK", "dependencias": {"base_de_datos": "OK", "modelo_xgboost": "OK", "features_modelo": 12}}`
- [x] La base de datos Supabase responde sin timeout
- [x] El modelo XGBoost se carga correctamente desde `data/models/modelo_xgboost_vitalrisk.pkl`

### Dashboard (Frontend)
- [x] El mapa de Antioquia se renderiza con municipios coloreados por IPT (verde/amarillo/rojo)
- [x] Los tooltips del mapa muestran nombre del municipio, IPT, casos IRA y PM2.5
- [x] Los 5 KPIs se cargan correctamente (municipios monitoreados, IPT VA, alertas activas, etc.)
- [x] El selector de año/semana interactúa con el backend y actualiza el mapa
- [x] La sección "Alertas Preventivas" carga las cards de alerta correctamente
- [x] La sección "Transparencia IA" muestra RMSE=1.7399, R²=0.607, 12 features
- [x] La descarga CSV desde "Datos Abiertos" genera un archivo con datos reales

### ETL Near-Real-Time
- [x] `POST /api/v1/etl/sincronizar?dias_atras=14` ejecuta sin error 500
- [x] El ETL procesa ≥ 30 municipios con datos de la semana actual
- [x] Los municipios aparecen coloreados en el mapa después del ETL

### Rendimiento
- [x] Tiempo de carga del dashboard (excluyendo cold start de Render): < 5 segundos
- [x] El endpoint `/mapa/riesgo` responde en < 3 segundos con BD activa
- [x] Cold start de Render (primera petición tras inactividad): ~45-60 segundos — **documentado como limitación conocida del plan gratuito**

---

## Limitaciones conocidas documentadas

| Limitación | Causa | Mitigación |
|---|---|---|
| Cold start 45-60 s | Render pausa servicios en plan gratuito por inactividad | Hacer una petición de "calentamiento" antes de la demo |
| Alertas todas en VERDE | SIVIGILA 2026 no tiene API pública — se usa media histórica como proxy | Documentado en Vista Transparencia IA del dashboard |
| PM2.5 con rezago ~6 meses | SISAIRE actualiza con rezago — se usa promedio histórico de BD | Documentado en Vista Transparencia IA del dashboard |

---

## Resultado: ✅ APROBADO

El sistema cumple con los criterios de aceptación de HU22. El MVP está listo para la defensa académica del 13 de julio de 2026.

*Firma: Equipo 326 — VitalRisk AI*