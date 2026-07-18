import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from models.pos import Venta, DetalleVenta, Pago
from models.suministro import Inventario

class POSService:
    @staticmethod
    def procesar_venta(
        session: Session,
        id_usuario: int,
        carrito: list[dict], # [{"producto": Producto, "cantidad": int}]
        total: float,
        id_medio_pago: int,
        id_cliente: int = None
    ) -> int:
        """
        Procesa una venta completa con garantías transaccionales ACID.
        Descuenta inventario, registra la cabecera de la venta, sus detalles y el pago.
        Si alguna operación falla, lanza ValueError o Exception y se debe manejar el rollback externo.
        Retorna el ID de la venta creada.
        """
        
        # 1. Validar y descontar stock (Lógica estricta)
        for item in carrito:
            prod = item["producto"]
            cant_requerida = item["cantidad"]
            
            # Buscar el inventario del producto ordenado por ID (o FIFO si hubiera lotes y fechas)
            inventarios = session.query(Inventario).filter(Inventario.idProducto == prod.idProducto).order_by(Inventario.idInventario).all()
            
            stock_disponible = sum(inv.cantidadDisponible for inv in inventarios)
            if stock_disponible < cant_requerida:
                raise ValueError(f"Stock insuficiente para {prod.nombre}. Requerido: {cant_requerida}, Disponible: {stock_disponible}")
                
            # Descuento FIFO
            cant_a_descontar = cant_requerida
            for inv in inventarios:
                if cant_a_descontar <= 0:
                    break
                if inv.cantidadDisponible >= cant_a_descontar:
                    inv.cantidadDisponible -= cant_a_descontar
                    cant_a_descontar = 0
                else:
                    cant_a_descontar -= inv.cantidadDisponible
                    inv.cantidadDisponible = 0

        # 2. Registrar Venta (Cabecera)
        nueva_venta = Venta(
            idCliente=id_cliente,
            idUsuario=id_usuario,
            fechaVenta=datetime.date.today(),
            montoTotal=total
        )
        session.add(nueva_venta)
        session.flush() # Para obtener el ID de la venta
        
        # 3. Registrar Detalles
        for item in carrito:
            prod = item["producto"]
            cant = item["cantidad"]
            precio = float(prod.precioLista)
            costo = float(prod.costoProducto)
            
            detalle = DetalleVenta(
                idVenta=nueva_venta.idVenta,
                idProducto=prod.idProducto,
                cantidad=cant,
                costoUnitario=costo,
                precioUnitario=precio,
                subtotal=cant * precio
            )
            session.add(detalle)
            
        # 4. Registrar Pago
        pago = Pago(
            idVenta=nueva_venta.idVenta,
            idMedioPago=id_medio_pago,
            fechaPago=datetime.date.today(),
            montoPagado=total
        )
        session.add(pago)
        
        # La transacción se completa y commitea en el controlador.
        return nueva_venta.idVenta
