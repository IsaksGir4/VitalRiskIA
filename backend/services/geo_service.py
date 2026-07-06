from utils import safe_float, safe_int

class GeoService:

    @staticmethod
    def build_geojson(rows: list, anio: int, semana_epi: int = None) -> dict:
        features = []
        for row in rows:
            features.append({
                "type": "Feature",
                "geometry": row.geometry,
                "properties": {
                    "codigo_dane":    row.codigo_dane,
                    "nombre":         row.nombre,
                    "subregion":      row.subregion,
                    "anio":           anio,
                    "ipt_score":      safe_float(row.ipt_score),
                    "nivel_riesgo":   row.nivel_riesgo,
                    "casos_ira_total":safe_int(row.casos_ira_total),
                    "tasa_ira_100k":  safe_float(row.tasa_ira_100k),
                    "pm25_avg":       safe_float(row.pm25_avg),
                }
            })
        return {
            "type":     "FeatureCollection",
            "features": features,
            "metadata": {
                "total_municipios": len(features),
                "anio":             anio,
                "semana_epi":       semana_epi,
                "fuente":           "VitalRisk AI — Equipo 326"
            }
        }