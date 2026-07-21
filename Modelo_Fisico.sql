CREATE DATABASE IF NOT EXISTS para_ti_boutique
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE para_ti_boutique;

-- 1. CATEGORÍAS
CREATE TABLE categoria (
    idCategoria INT AUTO_INCREMENT PRIMARY KEY,
    nombreCategoria VARCHAR(100) NOT NULL UNIQUE,
    estado VARCHAR(20) DEFAULT 'ACTIVO'
);

-- 2. PRODUCTOS
CREATE TABLE producto (
    idProducto INT AUTO_INCREMENT PRIMARY KEY,
    idCategoria INT NOT NULL,
    codigoBarras VARCHAR(100) NULL, 
    nombre VARCHAR(100) NOT NULL,
    talla VARCHAR(20) NULL,
    color VARCHAR(50) NULL,
    marca VARCHAR(50) NULL,
    material VARCHAR(50) NULL,
    costoProducto DECIMAL(10,2) NOT NULL,
    precioLista DECIMAL(10,2) NOT NULL,
    estado VARCHAR(20) DEFAULT 'ACTIVO',
    CONSTRAINT fk_producto_categoria FOREIGN KEY (idCategoria) REFERENCES categoria(idCategoria),
    UNIQUE KEY uq_codigo_barras (codigoBarras)
);
CREATE INDEX idx_producto_barras ON producto(codigoBarras);

-- 3. CLIENTES (Estandarizado con Nombres y Apellidos separados)
CREATE TABLE cliente (
    idCliente INT AUTO_INCREMENT PRIMARY KEY,
    tipoDocumento VARCHAR(20) NOT NULL DEFAULT 'DNI', -- DNI, RUC, PASAPORTE
    numeroDocumento VARCHAR(20) NOT NULL,
    nombres VARCHAR(100) NOT NULL,
    apellidos VARCHAR(100) NOT NULL,
    telefono VARCHAR(20) NULL,
    correoElectronico VARCHAR(100) NULL,
    estado VARCHAR(20) DEFAULT 'ACTIVO',
    UNIQUE KEY uq_cliente_documento (numeroDocumento)
);
CREATE INDEX idx_cliente_doc ON cliente(numeroDocumento);

-- 4. PROVEEDORES
CREATE TABLE proveedor (
    idProveedor INT AUTO_INCREMENT PRIMARY KEY,
    tipoDocumento VARCHAR(20) NOT NULL DEFAULT 'RUC',
    numeroDocumento VARCHAR(20) NOT NULL,
    nombreRazonSocial VARCHAR(150) NOT NULL,
    telefono VARCHAR(20) NULL,
    direccion VARCHAR(200) NULL,
    correoElectronico VARCHAR(100) NULL,
    estado VARCHAR(20) DEFAULT 'ACTIVO',
    UNIQUE KEY uq_proveedor_documento (numeroDocumento)
);

-- 5. USUARIOS Y SEGURIDAD (Ya contaba con esta estructura limpia)
CREATE TABLE usuario (
    idUsuario INT AUTO_INCREMENT PRIMARY KEY,
    nombres VARCHAR(100) NOT NULL,
    apellidos VARCHAR(100) NULL,
    nombreUsuario VARCHAR(50) NOT NULL UNIQUE,
    contrasena VARCHAR(100) NOT NULL,
    rol VARCHAR(50) NOT NULL DEFAULT 'CAJERO', -- ADMINISTRADOR, CAJERO, AUDITOR
    estado VARCHAR(20) DEFAULT 'ACTIVO'
);

-- 6. INVENTARIO
CREATE TABLE inventario (
    idProducto INT PRIMARY KEY,
    fechaActualizacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    cantidadDisponible INT NOT NULL DEFAULT 0,
    CONSTRAINT fk_inventario_producto FOREIGN KEY (idProducto) REFERENCES producto(idProducto)
);

-- 7. TRANSACCIONES: VENTAS
CREATE TABLE venta (
    idVenta INT AUTO_INCREMENT PRIMARY KEY,
    idCliente INT NULL,
    idUsuario INT NOT NULL,
    fechaVenta DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    montoTotal DECIMAL(10,2) NOT NULL,
    estadoVenta VARCHAR(20) DEFAULT 'COMPLETADA', -- COMPLETADA, ANULADA
    estadoPago VARCHAR(20) DEFAULT 'PAGADA',       -- PAGADA, PENDIENTE, PARCIAL
    CONSTRAINT fk_venta_cliente FOREIGN KEY (idCliente) REFERENCES cliente(idCliente),
    CONSTRAINT fk_venta_usuario FOREIGN KEY (idUsuario) REFERENCES usuario(idUsuario)
);
CREATE INDEX idx_venta_fecha ON venta(fechaVenta);

CREATE TABLE detalle_venta (
    idDetalleVenta INT AUTO_INCREMENT PRIMARY KEY,
    idVenta INT NOT NULL,
    idProducto INT NOT NULL,
    cantidad INT NOT NULL,
    costoUnitario DECIMAL(10,2) NOT NULL,
    precioUnitario DECIMAL(10,2) NOT NULL,
    subtotal DECIMAL(10,2) NOT NULL,
    CONSTRAINT fk_detalle_venta_venta FOREIGN KEY (idVenta) REFERENCES venta(idVenta),
    CONSTRAINT fk_detalle_venta_producto FOREIGN KEY (idProducto) REFERENCES producto(idProducto)
);

CREATE TABLE medio_pago (
    idMedioPago INT AUTO_INCREMENT PRIMARY KEY,
    nombreMedioPago VARCHAR(50) NOT NULL UNIQUE,
    estado VARCHAR(20) DEFAULT 'ACTIVO'
);

CREATE TABLE pago (
    idPago INT AUTO_INCREMENT PRIMARY KEY,
    idVenta INT NOT NULL,
    idMedioPago INT NOT NULL,
    fechaPago DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    montoPagado DECIMAL(10,2) NOT NULL,
    CONSTRAINT fk_pago_venta_ref FOREIGN KEY (idVenta) REFERENCES venta(idVenta),
    CONSTRAINT fk_pago_medio_ref FOREIGN KEY (idMedioPago) REFERENCES medio_pago(idMedioPago)
);

-- 8. TRANSACCIONES: COMPRAS
CREATE TABLE compra (
    idCompra INT AUTO_INCREMENT PRIMARY KEY,
    idProveedor INT NOT NULL,
    idUsuario INT NOT NULL,
    fechaCompra DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    montoTotal DECIMAL(10,2) NOT NULL,
    estado VARCHAR(20) DEFAULT 'Borrador',
    CONSTRAINT fk_compra_proveedor FOREIGN KEY (idProveedor) REFERENCES proveedor(idProveedor),
    CONSTRAINT fk_compra_usuario FOREIGN KEY (idUsuario) REFERENCES usuario(idUsuario)
);

CREATE TABLE detalle_compra (
    idDetalleCompra INT AUTO_INCREMENT PRIMARY KEY,
    idCompra INT NOT NULL,
    idProducto INT NOT NULL,
    cantidad INT NOT NULL,
    costoUnitario DECIMAL(10,2) NOT NULL,
    subtotal DECIMAL(10,2) NOT NULL,
    CONSTRAINT fk_detalle_compra_compra FOREIGN KEY (idCompra) REFERENCES compra(idCompra),
    CONSTRAINT fk_detalle_compra_producto FOREIGN KEY (idProducto) REFERENCES producto(idProducto)
);

-- 9. SOLICITUDES DE REPOSICIÓN
CREATE TABLE solicitud_reposicion (
    idSolicitud INT AUTO_INCREMENT PRIMARY KEY,
    idProducto INT NOT NULL,
    cantidad_sugerida INT NOT NULL DEFAULT 0,
    motivo VARCHAR(100) NOT NULL,
    origen VARCHAR(20) NOT NULL DEFAULT 'IA',
    estado VARCHAR(20) NOT NULL DEFAULT 'Pendiente',
    fecha_creacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_solicitud_producto FOREIGN KEY (idProducto) REFERENCES producto(idProducto)
);