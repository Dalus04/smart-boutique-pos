CREATE DATABASE IF NOT EXISTS para_ti_boutique
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE para_ti_boutique;

CREATE TABLE categoria (
    idCategoria INT AUTO_INCREMENT PRIMARY KEY,
    nombreCategoria VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE administrador (
    idAdministrador INT AUTO_INCREMENT PRIMARY KEY,
    nombres VARCHAR(100) NOT NULL,
    usuario VARCHAR(50) NOT NULL UNIQUE,
    contrasena VARCHAR(100) NOT NULL
);

CREATE TABLE usuario (
    idUsuario INT AUTO_INCREMENT PRIMARY KEY,
    idAdministrador INT NULL,
    nombres VARCHAR(100) NOT NULL,
    apellidos VARCHAR(100) NULL,
    nombreUsuario VARCHAR(50) NOT NULL UNIQUE,
    contrasena VARCHAR(100) NULL,
    rol VARCHAR(50) NULL,
    estado VARCHAR(20) NULL,
    CONSTRAINT fk_usuario_administrador
        FOREIGN KEY (idAdministrador)
        REFERENCES administrador(idAdministrador)
);

CREATE TABLE cliente (
    idCliente INT PRIMARY KEY,
    nombresCompletos VARCHAR(150) NOT NULL,
    telefono VARCHAR(20) NULL,
    correoElectronico VARCHAR(100) NULL
);

CREATE TABLE proveedor (
    idProveedor INT PRIMARY KEY,
    nombreRazonSocial VARCHAR(150) NOT NULL,
    telefono VARCHAR(20) NULL,
    direccion VARCHAR(200) NULL,
    correoElectronico VARCHAR(100) NULL
);

CREATE TABLE producto (
    idProducto INT AUTO_INCREMENT PRIMARY KEY,
    idCategoria INT NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    talla VARCHAR(20) NULL,
    color VARCHAR(50) NULL,
    marca VARCHAR(50) NULL,
    material VARCHAR(50) NULL,
    costoProducto DECIMAL(10,2) NOT NULL,
    precioLista DECIMAL(10,2) NOT NULL,
    CONSTRAINT fk_producto_categoria
        FOREIGN KEY (idCategoria)
        REFERENCES categoria(idCategoria)
);

CREATE TABLE inventario (
    idInventario INT AUTO_INCREMENT PRIMARY KEY,
    idProducto INT NOT NULL,
    fechaActualizacion DATE NOT NULL,
    cantidadDisponible INT NOT NULL,
    CONSTRAINT fk_inventario_producto
        FOREIGN KEY (idProducto)
        REFERENCES producto(idProducto)
);

CREATE TABLE venta (
    idVenta INT AUTO_INCREMENT PRIMARY KEY,
    idCliente INT NULL,
    idUsuario INT NOT NULL,
    fechaVenta DATE NOT NULL,
    montoTotal DECIMAL(10,2) NOT NULL,
    CONSTRAINT fk_venta_cliente
        FOREIGN KEY (idCliente)
        REFERENCES cliente(idCliente),
    CONSTRAINT fk_venta_usuario
        FOREIGN KEY (idUsuario)
        REFERENCES usuario(idUsuario)
);

CREATE TABLE detalle_venta (
    idDetalleVenta INT AUTO_INCREMENT PRIMARY KEY,
    idVenta INT NOT NULL,
    idProducto INT NOT NULL,
    cantidad INT NOT NULL,
    costoUnitario DECIMAL(10,2) NOT NULL,
    precioUnitario DECIMAL(10,2) NOT NULL,
    subtotal DECIMAL(10,2) NOT NULL,
    CONSTRAINT fk_detalle_venta_venta
        FOREIGN KEY (idVenta)
        REFERENCES venta(idVenta),
    CONSTRAINT fk_detalle_venta_producto
        FOREIGN KEY (idProducto)
        REFERENCES producto(idProducto)
);

CREATE TABLE medio_pago (
    idMedioPago INT AUTO_INCREMENT PRIMARY KEY,
    nombreMedioPago VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE pago (
    idPago INT AUTO_INCREMENT PRIMARY KEY,
    idVenta INT NOT NULL,
    idMedioPago INT NOT NULL,
    fechaPago DATE NOT NULL,
    montoPagado DECIMAL(10,2) NOT NULL,
    CONSTRAINT fk_pago_venta
        FOREIGN KEY (idVenta)
        REFERENCES venta(idVenta),
    CONSTRAINT fk_pago_medio_pago
        FOREIGN KEY (idMedioPago)
        REFERENCES medio_pago(idMedioPago)
);

CREATE TABLE compra (
    idCompra INT AUTO_INCREMENT PRIMARY KEY,
    idProveedor INT NOT NULL,
    idUsuario INT NOT NULL,
    fechaCompra DATE NOT NULL,
    montoTotal DECIMAL(10,2) NOT NULL,
    CONSTRAINT fk_compra_proveedor
        FOREIGN KEY (idProveedor)
        REFERENCES proveedor(idProveedor),
    CONSTRAINT fk_compra_usuario
        FOREIGN KEY (idUsuario)
        REFERENCES usuario(idUsuario)
);

CREATE TABLE detalle_compra (
    idDetalleCompra INT AUTO_INCREMENT PRIMARY KEY,
    idCompra INT NOT NULL,
    idProducto INT NOT NULL,
    cantidad INT NOT NULL,
    costoUnitario DECIMAL(10,2) NOT NULL,
    subtotal DECIMAL(10,2) NOT NULL,
    CONSTRAINT fk_detalle_compra_compra
        FOREIGN KEY (idCompra)
        REFERENCES compra(idCompra),
    CONSTRAINT fk_detalle_compra_producto
        FOREIGN KEY (idProducto)
        REFERENCES producto(idProducto)
);