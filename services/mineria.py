from collections import defaultdict
from itertools import combinations
from sqlalchemy.orm import Session
from models.pos import Venta, DetalleVenta

class MineriaService:
    # Diccionario de reglas: { antecedente_id: [(consecuente_id, confianza), ...] }
    _reglas: dict[int, list[tuple[int, float]]] = {}

    @classmethod
    def _extraer_transacciones(cls, session: Session) -> list[set[int]]:
        """
        Extrae las transacciones de la base de datos de manera eficiente con una única consulta.
        """
        from models.pos import DetalleVenta
        
        # Consulta de una sola llamada para obtener ID de venta y producto
        detalles = session.query(DetalleVenta.idVenta, DetalleVenta.idProducto).all()
        
        transacciones_map = defaultdict(set)
        for id_venta, id_producto in detalles:
            transacciones_map[id_venta].add(id_producto)
            
        return [prod_ids for prod_ids in transacciones_map.values() if prod_ids]

    @classmethod
    def entrenar_modelo(cls, session: Session, min_support: int = 2, min_confidence: float = 0.5):
        """
        Calcula las reglas de asociación de 2-itemsets y las almacena en memoria.
        """
        transacciones = cls._extraer_transacciones(session)
        
        # 1. Calcular soporte individual de cada producto
        item_support = defaultdict(int)
        for transaccion in transacciones:
            for item in transaccion:
                item_support[item] += 1
                
        # Filtrar por soporte mínimo
        frequent_items = {item for item, count in item_support.items() if count >= min_support}
        
        # 2. Calcular soporte de pares (2-itemsets)
        pair_support = defaultdict(int)
        for transaccion in transacciones:
            # Solo considerar los items frecuentes en esta transacción
            items_en_transaccion = [item for item in transaccion if item in frequent_items]
            # Generar combinaciones de 2 elementos ordenadas
            for pair in combinations(sorted(items_en_transaccion), 2):
                pair_support[pair] += 1
                
        # 3. Generar reglas (A -> B) y (B -> A) y calcular confianza
        reglas_temp = defaultdict(list)
        for pair, count in pair_support.items():
            if count >= min_support:
                item_a, item_b = pair
                
                # Regla A -> B
                conf_a_b = count / item_support[item_a]
                if conf_a_b >= min_confidence:
                    reglas_temp[item_a].append((item_b, conf_a_b))
                    
                # Regla B -> A
                conf_b_a = count / item_support[item_b]
                if conf_b_a >= min_confidence:
                    reglas_temp[item_b].append((item_a, conf_b_a))
                    
        # Ordenar reglas de cada antecedente por confianza descendente
        cls._reglas = {}
        for antecedente, consecuentes in reglas_temp.items():
            cls._reglas[antecedente] = sorted(consecuentes, key=lambda x: x[1], reverse=True)

    @classmethod
    def sugerir_venta_cruzada(cls, carrito_ids: list[int]) -> list[tuple[int, float]]:
        """
        Dado los IDs de productos en el carrito, retorna hasta 3 tuplas (id_producto, confianza) recomendadas.
        """
        recomendaciones_potenciales = defaultdict(float)
        
        for item_id in carrito_ids:
            if item_id in cls._reglas:
                for consecuente_id, confianza in cls._reglas[item_id]:
                    # Evitar recomendar algo que ya está en el carrito
                    if consecuente_id not in carrito_ids:
                        if confianza > recomendaciones_potenciales[consecuente_id]:
                            recomendaciones_potenciales[consecuente_id] = confianza
                            
        # Ordenar por confianza descendente y devolver el top 3
        top_sugerencias = sorted(recomendaciones_potenciales.items(), key=lambda x: x[1], reverse=True)
        return top_sugerencias[:3]

    @classmethod
    def obtener_mejores_reglas(cls, limit: int = 3) -> list[tuple[int, int, float]]:
        """
        Retorna las reglas más fuertes de la base de conocimiento global.
        Retorna: [(antecedente_id, consecuente_id, confianza)]
        """
        todas_las_reglas = []
        for antecedente, consecuentes in cls._reglas.items():
            for consecuente, confianza in consecuentes:
                todas_las_reglas.append((antecedente, consecuente, confianza))
                
        todas_las_reglas.sort(key=lambda x: x[2], reverse=True)
        return todas_las_reglas[:limit]

    @classmethod
    def obtener_insights(cls, metricas: dict) -> list[dict]:
        insights = []
        kpis = metricas.get("kpis", {})
        
        ventas_var = kpis.get("ventas", {}).get("var", 0)
        ventas_val = kpis.get("ventas", {}).get("valor", 0)
        
        # 1. Resumen principal
        resumen = "Rendimiento estable."
        if ventas_var > 0:
            resumen = f"Tu negocio está creciendo. Has recaudado ${ventas_val:,.2f} con un incremento del {ventas_var:.1f}% respecto al periodo anterior."
        elif ventas_var < 0:
            resumen = f"Precaución: Las ventas han caído un {abs(ventas_var):.1f}% respecto al periodo anterior."
        
        insights.append({
            "tipo": "resumen",
            "mensaje": resumen,
            "icono": "📋"
        })
        
        # Oportunidades y Riesgos basados en KPI
        margen = kpis.get("margen", {}).get("valor", 0)
        if margen < 30: # umbral genérico
            insights.append({
                "tipo": "riesgo", 
                "mensaje": f"Margen bruto bajo ({margen:.1f}%). Revisa costos.", 
                "icono": "🔴",
                "accion_texto": "Revisar Catálogo",
                "accion_target": "catalogo"
            })
            
        # Tareas basadas en Inventario
        salud = metricas.get("salud_inventario", {})
        criticos = salud.get("Crítico", {}).get("items", 0)
        if criticos > 0:
            insights.append({
                "tipo": "tarea", 
                "mensaje": f"Tienes {criticos} productos en stock crítico.", 
                "icono": "🔵",
                "accion_texto": "Ir a Inventario",
                "accion_target": "inventario"
            })
        else:
            insights.append({"tipo": "oportunidad", "mensaje": "Inventario sano, sin quiebres urgentes.", "icono": "🟢"})
            
        # Oportunidades basadas en reglas de asociación
        reglas = metricas.get("reglas", [])
        for a, c, conf in reglas:
            if a and c:
                insights.append({"tipo": "oportunidad", "mensaje": f"Sugerencia: Promocionar {a} con {c} (Prob: {conf*100:.0f}%).", "icono": "💡"})
                
        return insights
