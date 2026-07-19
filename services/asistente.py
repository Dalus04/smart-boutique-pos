from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any
from decimal import Decimal

from models.actores import Cliente
from models.catalogo import Producto
from models.pos import Venta
from services.mineria import MineriaService

class AsistenteComercialService:
    """
    Fachada (Facade) que orquesta la inteligencia comercial para el POS.
    Integra minería de datos (Apriori), inventario, rentabilidad y contexto del cliente.
    """

    @staticmethod
    def analizar_cliente(db: Session, cliente_id: int) -> Dict[str, Any]:
        """
        Calcula el contexto RFM (Recencia, Frecuencia, Valor Monetario) del cliente.
        """
        cliente = db.query(Cliente).get(cliente_id)
        if not cliente:
            return {}

        stats = db.query(
            func.max(Venta.fechaVenta).label('ultima_compra'),
            func.avg(Venta.montoTotal).label('ticket_promedio'),
            func.count(Venta.idVenta).label('frecuencia_compra')
        ).filter(Venta.idCliente == cliente_id).first()

        frecuencia = stats.frecuencia_compra if stats and stats.frecuencia_compra else 0
        ticket_promedio = float(stats.ticket_promedio) if stats and stats.ticket_promedio else 0.0
        ultima_compra = stats.ultima_compra.isoformat() if stats and stats.ultima_compra else None

        # Clasificación heurística
        clasificacion = "Nuevo"
        if frecuencia >= 10:
            clasificacion = "VIP"
        elif frecuencia >= 3:
            clasificacion = "Frecuente"
        elif frecuencia > 0:
            clasificacion = "Regular"

        return {
            "idCliente": cliente.idCliente,
            "nombres": cliente.nombres,
            "apellidos": cliente.apellidos,
            "clasificacion": clasificacion,
            "frecuencia_compra": frecuencia,
            "ticket_promedio": ticket_promedio,
            "ultima_compra": ultima_compra
        }

    @staticmethod
    def evaluar_salud_producto(producto: Producto) -> Dict[str, Any]:
        """
        Evalúa el estado del stock y la rentabilidad del producto.
        """
        stock = producto.inventario.cantidadDisponible if producto.inventario else 0
        
        margen = 0.0
        if producto.precioLista and producto.precioLista > 0:
            margen = ((float(producto.precioLista) - float(producto.costoProducto)) / float(producto.precioLista)) * 100
            
        estado_stock = "Óptimo"
        if stock <= 5:
            estado_stock = "Crítico"
        elif stock <= 15:
            estado_stock = "Bajo"
            
        return {
            "idProducto": producto.idProducto,
            "nombre": producto.nombre,
            "precio": float(producto.precioLista) if producto.precioLista else 0.0,
            "costo": float(producto.costoProducto) if producto.costoProducto else 0.0,
            "stock": stock,
            "margen": margen,
            "estado_stock": estado_stock
        }

    @staticmethod
    def generar_contexto_comercial(db: Session, carrito_ids: List[int], id_cliente: int = None) -> Dict[str, Any]:
        """
        Construye un estado inteligente del ticket consolidando:
        - Cliente
        - Sugerencias Cruzadas (Apriori)
        """
        contexto = {
            "cliente": None,
            "ticket": {}, # Se puede extender luego si se pasa el carrito completo
            "cross_sell": [],
            "inventario": [] # Se podría poblar con alertas de los items del ticket
        }

        # 1. Analizar Cliente
        if id_cliente:
            contexto["cliente"] = AsistenteComercialService.analizar_cliente(db, id_cliente)

        # 2. Venta Cruzada (Apriori)
        if carrito_ids:
            sugerencias_tuplas = MineriaService.sugerir_venta_cruzada(carrito_ids)
            
            for antecedente_id, consecuente_id, conf, sop, lift, tipo in sugerencias_tuplas:
                consecuente = db.query(Producto).get(consecuente_id)
                antecedente = db.query(Producto).get(antecedente_id)
                
                if consecuente and consecuente.inventario and consecuente.inventario.cantidadDisponible > 0:
                    explicacion = f"Frecuentemente comprado junto con '{antecedente.nombre}'"
                    
                    contexto["cross_sell"].append({
                        "idProducto": consecuente.idProducto,
                        "nombre": consecuente.nombre,
                        "precio": float(consecuente.precioLista),
                        "tipo_recomendacion": "Complemento Recomendado",
                        "justificacion": {
                            "antecedente_id": antecedente.idProducto,
                            "antecedente_nombre": antecedente.nombre,
                            "texto": explicacion,
                            "soporte": sop,
                            "confianza": conf,
                            "lift": lift
                        }
                    })

        return contexto
