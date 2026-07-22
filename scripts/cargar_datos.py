import datetime
import pandas as pd
import mysql.connector
from mysql.connector import Error

import os
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(BASE_DIR, ".env"))

from config.settings import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_PORT

# =========================================================
# CONFIGURACIÓN
# =========================================================
RUTA_EXCEL = os.path.join(BASE_DIR, "data", "TIENDA_ROPA_FINAL.xlsx")

CONFIG_BD = {
    "host": DB_HOST,
    "user": DB_USER,
    "password": DB_PASSWORD,
    "database": DB_NAME,
    "port": int(DB_PORT)
}

# =========================================================
# FUNCIONES AUXILIARES
# =========================================================
def adelantar_un_ano_si_posible(fecha):
    if pd.isnull(fecha) or fecha is None:
        return fecha
    
    fecha_dt = pd.to_datetime(fecha)
    hoy = pd.to_datetime(datetime.date.today())
    
    try:
        fecha_proyectada = fecha_dt.replace(year=fecha_dt.year + 1)
    except ValueError:
        # Manejo para años bisiestos (ej. 29 de febrero)
        fecha_proyectada = fecha_dt + pd.DateOffset(years=1)
        
    if fecha_proyectada <= hoy:
        return fecha_proyectada.date()
    return fecha_dt.date()


def obtener_o_insertar_categoria(cursor, nombre_categoria):
    cursor.execute(
        "SELECT idCategoria FROM categoria WHERE nombreCategoria = %s",
        (nombre_categoria,)
    )
    resultado = cursor.fetchone()

    if resultado:
        return resultado[0]

    cursor.execute(
        "INSERT INTO categoria (nombreCategoria) VALUES (%s)",
        (nombre_categoria,)
    )
    return cursor.lastrowid


def obtener_o_insertar_cliente(cursor, id_cliente, nombre_cliente):
    cursor.execute(
        "SELECT idCliente FROM cliente WHERE idCliente = %s",
        (int(id_cliente),)
    )
    resultado = cursor.fetchone()

    if resultado:
        return resultado[0]

    # Separar nombre completo en nombres y apellidos si es posible
    partes = str(nombre_cliente).strip().split(" ", 1)
    nombres = partes[0]
    apellidos = partes[1] if len(partes) > 1 else "-"
    doc_cliente = f"CLI-{int(id_cliente):05d}"

    cursor.execute(
        """
        INSERT INTO cliente (idCliente, tipoDocumento, numeroDocumento, nombres, apellidos, telefono, correoElectronico)
        VALUES (%s, 'DNI', %s, %s, %s, NULL, NULL)
        """,
        (int(id_cliente), doc_cliente, nombres, apellidos)
    )
    return int(id_cliente)


def obtener_o_insertar_proveedor(cursor, id_proveedor, nombre_proveedor):
    cursor.execute(
        "SELECT idProveedor FROM proveedor WHERE idProveedor = %s",
        (int(id_proveedor),)
    )
    resultado = cursor.fetchone()

    if resultado:
        return resultado[0]

    doc_prov = f"PROV-{int(id_proveedor):05d}"

    cursor.execute(
        """
        INSERT INTO proveedor
        (idProveedor, tipoDocumento, numeroDocumento, nombreRazonSocial, telefono, direccion, correoElectronico)
        VALUES (%s, 'RUC', %s, %s, NULL, NULL, NULL)
        """,
        (int(id_proveedor), doc_prov, nombre_proveedor)
    )
    return int(id_proveedor)


def determinar_rol(nombre_usuario):
    usuario = nombre_usuario.strip().lower()

    if "admin" in usuario:
        return "ADMINISTRADOR"
    elif "auditor" in usuario:
        return "AUDITOR"
    else:
        return "CAJERO"


def obtener_o_insertar_usuario(cursor, nombre_usuario):
    nombre_usuario = nombre_usuario.strip()
    rol = determinar_rol(nombre_usuario)

    cursor.execute(
        "SELECT idUsuario FROM usuario WHERE nombreUsuario = %s",
        (nombre_usuario,)
    )
    resultado = cursor.fetchone()

    if resultado:
        return resultado[0]

    partes = nombre_usuario.split(" ", 1)
    nombres = partes[0]
    apellidos = partes[1] if len(partes) > 1 else "-"

    cursor.execute(
        """
        INSERT INTO usuario
        (nombres, apellidos, nombreUsuario, contrasena, rol, estado)
        VALUES (%s, %s, %s, '123456', %s, 'ACTIVO')
        """,
        (nombres, apellidos, nombre_usuario, rol)
    )
    return cursor.lastrowid


def obtener_o_insertar_producto(
    cursor,
    id_categoria,
    nombre_producto,
    costo_unitario,
    precio_lista
):
    cursor.execute(
        """
        SELECT idProducto
        FROM producto
        WHERE nombre = %s AND idCategoria = %s
        """,
        (nombre_producto, id_categoria)
    )
    resultado = cursor.fetchone()

    if resultado:
        id_producto = resultado[0]

        # Actualizar costo y precio vigente del catálogo
        cursor.execute(
            """
            UPDATE producto
            SET costoProducto = %s,
                precioLista = %s
            WHERE idProducto = %s
            """,
            (
                float(costo_unitario),
                float(precio_lista),
                id_producto
            )
        )

        return id_producto

    # Si no existe, insertarlo
    cursor.execute(
        """
        INSERT INTO producto
        (
            idCategoria,
            nombre,
            talla,
            color,
            marca,
            material,
            costoProducto,
            precioLista
        )
        VALUES (%s, %s, NULL, NULL, NULL, NULL, %s, %s)
        """,
        (
            id_categoria,
            nombre_producto,
            float(costo_unitario),
            float(precio_lista)
        )
    )

    return cursor.lastrowid


def insertar_o_actualizar_inventario(cursor, id_producto, fecha_registro, stock_actual):
    cursor.execute(
        "SELECT idProducto FROM inventario WHERE idProducto = %s",
        (id_producto,)
    )
    resultado = cursor.fetchone()

    if resultado:
        cursor.execute(
            """
            UPDATE inventario
            SET fechaActualizacion = %s,
                cantidadDisponible = %s
            WHERE idProducto = %s
            """,
            (fecha_registro, int(stock_actual), id_producto)
        )
    else:
        cursor.execute(
            """
            INSERT INTO inventario
            (idProducto, fechaActualizacion, cantidadDisponible)
            VALUES (%s, %s, %s)
            """,
            (id_producto, fecha_registro, int(stock_actual))
        )


def insertar_venta_si_no_existe(cursor, id_venta, id_cliente, id_usuario, fecha_venta, total):
    cursor.execute(
        "SELECT idVenta FROM venta WHERE idVenta = %s",
        (int(id_venta),)
    )
    resultado = cursor.fetchone()

    if not resultado:
        cursor.execute(
            """
            INSERT INTO venta
            (idVenta, idCliente, idUsuario, fechaVenta, montoTotal)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (int(id_venta), id_cliente, id_usuario, fecha_venta, float(total))
        )


def insertar_detalle_venta_si_no_existe(
    cursor,
    id_venta,
    id_producto,
    cantidad,
    costo_unitario,
    precio_unitario
):
    subtotal = float(cantidad) * float(precio_unitario)

    cursor.execute(
        """
        SELECT idDetalleVenta
        FROM detalle_venta
        WHERE idVenta = %s AND idProducto = %s
        """,
        (int(id_venta), id_producto)
    )
    resultado = cursor.fetchone()

    if not resultado:
        cursor.execute(
            """
            INSERT INTO detalle_venta
            (
                idVenta,
                idProducto,
                cantidad,
                costoUnitario,
                precioUnitario,
                subtotal
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                int(id_venta),
                id_producto,
                int(cantidad),
                float(costo_unitario),
                float(precio_unitario),
                subtotal
            )
        )


def obtener_o_insertar_medio_pago(cursor, nombre_medio_pago):
    cursor.execute(
        "SELECT idMedioPago FROM medio_pago WHERE nombreMedioPago = %s",
        (nombre_medio_pago,)
    )
    resultado = cursor.fetchone()

    if resultado:
        return resultado[0]

    cursor.execute(
        "INSERT INTO medio_pago (nombreMedioPago) VALUES (%s)",
        (nombre_medio_pago,)
    )
    return cursor.lastrowid


def insertar_pago_si_no_existe(cursor, id_venta, id_medio_pago, fecha_pago, monto_pagado):
    cursor.execute(
        "SELECT idPago FROM pago WHERE idVenta = %s",
        (int(id_venta),)
    )
    resultado = cursor.fetchone()

    if not resultado:
        cursor.execute(
            """
            INSERT INTO pago
            (idVenta, idMedioPago, fechaPago, montoPagado)
            VALUES (%s, %s, %s, %s)
            """,
            (
                int(id_venta),
                id_medio_pago,
                fecha_pago,
                float(monto_pagado)
            )
        )


def insertar_compra_y_detalle_si_no_existe(
    cursor,
    id_proveedor,
    id_usuario,
    fecha_compra,
    id_producto,
    cantidad,
    costo_unitario
):
    subtotal = float(cantidad) * float(costo_unitario)

    # 1. Buscar si ya existe una compra creada para este proveedor, usuario y fecha exacta
    cursor.execute(
        """
        SELECT idCompra FROM compra
        WHERE idProveedor = %s AND idUsuario = %s AND fechaCompra = %s
        """,
        (int(id_proveedor), id_usuario, fecha_compra)
    )
    resultado_compra = cursor.fetchone()

    if resultado_compra:
        id_compra = resultado_compra[0]
        # Sumar el subtotal al montoTotal de la compra
        cursor.execute(
            "UPDATE compra SET montoTotal = montoTotal + %s WHERE idCompra = %s",
            (subtotal, id_compra)
        )
    else:
        # Crear nueva compra
        cursor.execute(
            """
            INSERT INTO compra (idProveedor, idUsuario, fechaCompra, montoTotal, estado)
            VALUES (%s, %s, %s, %s, 'Completada')
            """,
            (int(id_proveedor), id_usuario, fecha_compra, subtotal)
        )
        id_compra = cursor.lastrowid

    # 2. Insertar el detalle de la compra si no existe
    cursor.execute(
        """
        SELECT idDetalleCompra FROM detalle_compra
        WHERE idCompra = %s AND idProducto = %s
        """,
        (id_compra, id_producto)
    )
    if not cursor.fetchone():
        cursor.execute(
            """
            INSERT INTO detalle_compra (idCompra, idProducto, cantidad, costoUnitario, subtotal)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (id_compra, id_producto, int(cantidad), float(costo_unitario), subtotal)
        )


# =========================================================
# PROCESO PRINCIPAL DE CARGA
# =========================================================
def cargar_datos():
    conexion = None

    try:
        # Leer Excel
        datos = pd.read_excel(RUTA_EXCEL)

        # Convertir y adelantar fechas 1 año si no supera el día de hoy
        datos["Fecha"] = datos["Fecha"].apply(adelantar_un_ano_si_posible)
        datos["Fecha_Registro"] = datos["Fecha_Registro"].apply(adelantar_un_ano_si_posible)

        # Conectar a MySQL
        conexion = mysql.connector.connect(**CONFIG_BD)
        cursor = conexion.cursor()

        print("Conexión exitosa a MySQL.")
        print(f"Registros leídos del Excel: {len(datos)}")

        ventas_cargadas = 0
        detalles_cargados = 0

        for _, fila in datos.iterrows():
            id_categoria = obtener_o_insertar_categoria(
                cursor,
                str(fila["Categoria"]).strip()
            )

            obtener_o_insertar_cliente(
                cursor,
                fila["ID_Cliente"],
                str(fila["Nombre_Cliente"]).strip()
            )

            obtener_o_insertar_proveedor(
                cursor,
                fila["ID_Proveedor"],
                str(fila["Proveedor"]).strip()
            )

            id_usuario = obtener_o_insertar_usuario(
                cursor,
                str(fila["Usuario_Registro"]).strip()
            )

            id_producto = obtener_o_insertar_producto(
                cursor,
                id_categoria,
                str(fila["Producto"]).strip(),
                fila["Costo_Unitario"],
                fila["Precio_Unitario"]
            )   

            insertar_o_actualizar_inventario(
                cursor,
                id_producto,
                fila["Fecha_Registro"],
                fila["Stock_Actual"]
            )

            cursor.execute(
                "SELECT idVenta FROM venta WHERE idVenta = %s",
                (int(fila["ID_Venta"]),)
            )
            venta_existente = cursor.fetchone()

            insertar_venta_si_no_existe(
                cursor,
                fila["ID_Venta"],
                int(fila["ID_Cliente"]),
                id_usuario,
                fila["Fecha"],
                fila["Total"]
            )

            if not venta_existente:
                ventas_cargadas += 1

            cursor.execute(
                """
                SELECT idDetalleVenta
                FROM detalle_venta
                WHERE idVenta = %s AND idProducto = %s
                """,
                (int(fila["ID_Venta"]), id_producto)
            )
            detalle_existente = cursor.fetchone()

            insertar_detalle_venta_si_no_existe(
                cursor,
                fila["ID_Venta"],
                id_producto,
                fila["Cantidad"],
                fila["Costo_Unitario"],
                fila["Precio_Unitario"]
            )

            if not detalle_existente:
                detalles_cargados += 1

            id_medio_pago = obtener_o_insertar_medio_pago(
                cursor,
                str(fila["Metodo_Pago"]).strip()
            )

            insertar_pago_si_no_existe(
                cursor,
                fila["ID_Venta"],
                id_medio_pago,
                fila["Fecha"],
                fila["Total"]
            )

            # Insertar compra y detalle de compra alineados con la fecha de venta y el proveedor
            insertar_compra_y_detalle_si_no_existe(
                cursor,
                fila["ID_Proveedor"],
                id_usuario,
                fila["Fecha"],
                id_producto,
                fila["Cantidad"],
                fila["Costo_Unitario"]
            )

        conexion.commit()

        print("Carga finalizada correctamente.")
        print(f"Ventas nuevas cargadas: {ventas_cargadas}")
        print(f"Detalles de venta nuevos cargados: {detalles_cargados}")

    except Error as error:
        print(f"Error de MySQL: {error}")

        if conexion:
            conexion.rollback()

    except Exception as error:
        print(f"Error durante la carga: {error}")

        if conexion:
            conexion.rollback()

    finally:
        if conexion and conexion.is_connected():
            cursor.close()
            conexion.close()
            print("Conexión cerrada.")


if __name__ == "__main__":
    cargar_datos()