-- phpMyAdmin SQL Dump
-- version 5.2.2
-- https://www.phpmyadmin.net/
--
-- Servidor: localhost:3306
-- Tiempo de generación: 17-05-2026 a las 16:07:39
-- Versión del servidor: 11.4.10-MariaDB
-- Versión de PHP: 8.4.21

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Base de datos: `siste234_Mi_querido_lomito`
--

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `caja`
--

CREATE TABLE `caja` (
  `id` int(11) NOT NULL,
  `fecha_apertura` timestamp NOT NULL DEFAULT current_timestamp(),
  `monto_inicial` decimal(10,2) DEFAULT NULL,
  `fecha_cierre` timestamp NULL DEFAULT NULL,
  `monto_final` decimal(10,2) DEFAULT NULL,
  `diferencia` decimal(10,2) DEFAULT NULL,
  `estado` varchar(20) DEFAULT 'abierta'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_spanish2_ci;

--
-- Volcado de datos para la tabla `caja`
--

INSERT INTO `caja` (`id`, `fecha_apertura`, `monto_inicial`, `fecha_cierre`, `monto_final`, `diferencia`, `estado`) VALUES
(1, '2026-02-28 11:15:43', 1000.00, '2026-03-03 11:12:37', 1500.00, 500.00, 'cerrada'),
(2, '2026-03-03 11:12:57', 1000.00, '2026-03-03 11:35:49', 1000.00, 0.00, 'cerrada'),
(3, '2026-03-14 17:35:09', 300.00, '2026-03-14 17:37:24', 1200.00, 900.00, 'cerrada'),
(4, '2026-03-14 17:40:48', 1200.00, '2026-03-22 05:42:20', 1480.00, 280.00, 'cerrada'),
(5, '2026-03-22 05:42:37', 1480.00, '2026-03-22 05:42:46', 1200.00, -280.00, 'cerrada'),
(6, '2026-03-22 05:43:01', 1000.00, '2026-03-22 05:51:17', 1000.00, 0.00, 'cerrada'),
(7, '2026-03-23 17:04:53', 500.00, '2026-04-05 17:08:25', 500.00, 0.00, 'cerrada'),
(8, '2026-04-06 16:22:33', 500.00, '2026-04-07 21:51:29', 500.00, 0.00, 'cerrada'),
(9, '2026-04-22 23:13:47', 500.00, '2026-04-28 18:33:51', 500.00, 0.00, 'cerrada');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `citas`
--

CREATE TABLE `citas` (
  `id` int(11) NOT NULL,
  `mascota_id` int(11) DEFAULT NULL,
  `servicio_id` int(11) DEFAULT NULL,
  `fecha` datetime DEFAULT NULL,
  `estado` enum('Pendiente','Completada','Cancelada') DEFAULT 'Pendiente',
  `notas` text DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_spanish2_ci;

--
-- Volcado de datos para la tabla `citas`
--

INSERT INTO `citas` (`id`, `mascota_id`, `servicio_id`, `fecha`, `estado`, `notas`) VALUES
(1, 1, NULL, '2026-02-28 11:30:00', 'Completada', NULL),
(2, 1, NULL, '2026-02-28 11:30:00', 'Cancelada', NULL),
(3, 2, NULL, '2026-03-20 14:15:00', 'Cancelada', NULL),
(4, 5, NULL, '2026-03-14 16:30:00', 'Cancelada', NULL),
(5, 6, NULL, '2026-03-14 12:00:00', 'Cancelada', NULL),
(6, 7, NULL, '2026-03-14 12:08:00', 'Cancelada', NULL),
(7, 6, NULL, '2026-03-14 13:00:00', 'Completada', NULL),
(8, 7, NULL, '2026-03-14 13:30:00', 'Cancelada', NULL),
(9, 8, NULL, '2026-03-19 10:00:00', 'Cancelada', NULL),
(10, 1, NULL, '2026-03-22 11:22:00', 'Cancelada', NULL),
(11, 11, NULL, '2026-04-24 10:00:00', 'Completada', NULL);

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `clientes`
--

CREATE TABLE `clientes` (
  `id` int(11) NOT NULL,
  `nombre` varchar(100) DEFAULT NULL,
  `telefono` varchar(20) DEFAULT NULL,
  `email` varchar(100) DEFAULT NULL,
  `direccion` text DEFAULT NULL,
  `fecha_registro` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_spanish2_ci;

--
-- Volcado de datos para la tabla `clientes`
--

INSERT INTO `clientes` (`id`, `nombre`, `telefono`, `email`, `direccion`, `fecha_registro`) VALUES
(1, 'América', '7541534362', 'alme9206@gmail.com', NULL, '2026-02-28 10:08:25'),
(2, 'ALONDRA AGUILLON RINCON', '55122383748739', 'ALONSFDSDF@GMAIL.COM', NULL, '2026-03-01 03:00:15'),
(3, 'EMMANUEL', '5581666396', '3A cOMALTECOS 19', NULL, '2026-03-01 03:03:09'),
(4, 'ITZAYANA DIAZ GALLEGOS', '5527088709', '', NULL, '2026-03-14 17:28:16'),
(5, 'NIEVES FERNANDA MORENO NUÑEZ', '5528832914', 'florecita130385@gmail.com', NULL, '2026-03-14 18:07:24');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `corte_caja`
--

CREATE TABLE `corte_caja` (
  `id` int(11) NOT NULL,
  `fecha` timestamp NOT NULL DEFAULT current_timestamp(),
  `total_ventas` decimal(10,2) DEFAULT NULL,
  `cantidad_ventas` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_spanish2_ci;

--
-- Volcado de datos para la tabla `corte_caja`
--

INSERT INTO `corte_caja` (`id`, `fecha`, `total_ventas`, `cantidad_ventas`) VALUES
(1, '2026-02-25 07:11:52', 0.00, 0),
(2, '2026-02-25 07:53:28', 0.00, 0),
(3, '2026-02-28 08:02:44', 0.00, 0),
(4, '2026-02-28 08:03:16', 0.00, 0),
(5, '2026-02-28 08:03:19', 0.00, 0),
(6, '2026-02-28 08:03:24', 0.00, 0),
(7, '2026-02-28 08:21:39', 0.00, 0),
(8, '2026-02-28 08:35:28', 0.00, 0);

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `detalle_venta`
--

CREATE TABLE `detalle_venta` (
  `id` int(11) NOT NULL,
  `venta_id` int(11) DEFAULT NULL,
  `tipo` enum('producto','servicio') DEFAULT NULL,
  `producto_id` int(11) DEFAULT NULL,
  `servicio_id` int(11) DEFAULT NULL,
  `cantidad` int(11) DEFAULT NULL,
  `precio_unitario` decimal(10,2) DEFAULT NULL,
  `subtotal` decimal(10,2) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_spanish2_ci;

--
-- Volcado de datos para la tabla `detalle_venta`
--

INSERT INTO `detalle_venta` (`id`, `venta_id`, `tipo`, `producto_id`, `servicio_id`, `cantidad`, `precio_unitario`, `subtotal`) VALUES
(5, 4, 'servicio', NULL, 1, 1, 50.00, 50.00),
(6, 4, 'servicio', NULL, 1, 1, 50.00, 50.00),
(7, 5, 'servicio', NULL, 1, 1, 50.00, 50.00),
(8, 6, 'producto', 1, NULL, 1, 155.00, 155.00),
(9, 6, 'producto', 1, NULL, 1, 155.00, 155.00),
(10, 6, 'producto', 1, NULL, 1, 155.00, 155.00),
(11, 6, 'servicio', NULL, 1, 1, 50.00, 50.00),
(12, 6, 'servicio', NULL, 1, 1, 50.00, 50.00),
(13, 7, 'producto', 1, NULL, 1, 155.00, 155.00),
(14, 7, 'producto', 3, NULL, 1, 25.00, 25.00),
(15, 8, 'producto', 1, NULL, 1, 155.00, 155.00),
(16, 8, 'servicio', NULL, 1, 1, 50.00, 50.00),
(17, 8, 'producto', 3, NULL, 1, 25.00, 25.00),
(18, 9, 'producto', 2, NULL, 1, 250.00, 250.00),
(19, 9, 'servicio', NULL, 1, 1, 50.00, 50.00),
(20, 10, 'servicio', NULL, 2, 1, 250.00, 250.00),
(21, 11, 'servicio', NULL, 3, 1, 320.00, 320.00),
(22, 12, 'servicio', NULL, 5, 1, 280.00, 280.00),
(23, 13, 'servicio', NULL, 5, 1, 280.00, 280.00);

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `entradas_inventario`
--

CREATE TABLE `entradas_inventario` (
  `id` int(11) NOT NULL,
  `producto_id` int(11) DEFAULT NULL,
  `cantidad` int(11) DEFAULT NULL,
  `fecha` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_spanish2_ci;

--
-- Volcado de datos para la tabla `entradas_inventario`
--

INSERT INTO `entradas_inventario` (`id`, `producto_id`, `cantidad`, `fecha`) VALUES
(1, 1, 1, '2026-03-01 02:54:18'),
(2, 1, 1, '2026-03-01 02:54:32'),
(3, 1, 20, '2026-03-01 02:54:43'),
(4, 3, 1, '2026-03-14 17:35:33'),
(5, 3, 115, '2026-03-14 17:35:42');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `gastos_fijos`
--

CREATE TABLE `gastos_fijos` (
  `id` int(11) NOT NULL,
  `concepto` varchar(100) DEFAULT NULL,
  `monto` decimal(10,2) DEFAULT NULL,
  `fecha` date DEFAULT NULL,
  `descripcion` text DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_spanish2_ci;

--
-- Volcado de datos para la tabla `gastos_fijos`
--

INSERT INTO `gastos_fijos` (`id`, `concepto`, `monto`, `fecha`, `descripcion`) VALUES
(1, 'Luz CFE', 1976.00, '2026-02-02', 'PAGO DE LUZ 2do Periodo'),
(2, 'Internet y Telefonía Totalplay', 410.00, '2026-02-23', 'Pago de totalplay mensual');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `insumos`
--

CREATE TABLE `insumos` (
  `id` int(11) NOT NULL,
  `nombre` varchar(100) DEFAULT NULL,
  `stock` int(11) DEFAULT NULL,
  `costo` decimal(10,2) DEFAULT NULL,
  `proveedor` varchar(100) DEFAULT NULL,
  `fecha` timestamp NOT NULL DEFAULT current_timestamp(),
  `codigo_barras` varchar(50) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_spanish2_ci;

--
-- Volcado de datos para la tabla `insumos`
--

INSERT INTO `insumos` (`id`, `nombre`, `stock`, `costo`, `proveedor`, `fecha`, `codigo_barras`) VALUES
(1, 'Shampoo para perro', 20, 150.00, 'Mixiuhca local 10', '2026-02-28 11:10:42', '2001151'),
(2, 'Moño para perros', 25, 20.00, 'Mixiuhca Local 2', '2026-02-28 11:13:10', '200122');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `mascotas`
--

CREATE TABLE `mascotas` (
  `id` int(11) NOT NULL,
  `cliente_id` int(11) DEFAULT NULL,
  `nombre` varchar(100) DEFAULT NULL,
  `especie` enum('Perro','Gato') DEFAULT NULL,
  `raza` varchar(100) DEFAULT NULL,
  `edad` int(11) DEFAULT NULL,
  `notas` text DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_spanish2_ci;

--
-- Volcado de datos para la tabla `mascotas`
--

INSERT INTO `mascotas` (`id`, `cliente_id`, `nombre`, `especie`, `raza`, `edad`, `notas`) VALUES
(1, 1, 'Nacho Lopez', 'Perro', NULL, NULL, NULL),
(2, 2, 'IRIS', 'Gato', NULL, NULL, NULL),
(4, 3, 'Loba', 'Perro', NULL, NULL, NULL),
(5, 1, 'Laysa', 'Perro', NULL, NULL, NULL),
(6, 4, 'MIMI', 'Perro', NULL, NULL, NULL),
(7, 5, 'KIRA', 'Perro', NULL, NULL, NULL),
(8, 1, 'KEY', 'Perro', NULL, NULL, NULL),
(9, 2, 'BERNARDO PELUCHIN', 'Perro', NULL, NULL, NULL),
(11, 1, 'Teo', 'Gato', NULL, NULL, NULL);

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `productos`
--

CREATE TABLE `productos` (
  `id` int(11) NOT NULL,
  `nombre` varchar(100) DEFAULT NULL,
  `stock` int(11) DEFAULT NULL,
  `precio` decimal(10,2) DEFAULT NULL,
  `costo` decimal(10,2) DEFAULT NULL,
  `codigo_barras` varchar(100) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_spanish2_ci;

--
-- Volcado de datos para la tabla `productos`
--

INSERT INTO `productos` (`id`, `nombre`, `stock`, `precio`, `costo`, `codigo_barras`) VALUES
(1, 'Cepillo de Pines Paw Brothers', 2, 378.00, NULL, '200501'),
(2, 'Correa gruesa de 1.5 mts', 3, 230.00, NULL, '200502'),
(3, 'Correa con Pechera y collar', 3, 230.00, NULL, '200503'),
(4, 'Correa Doble ', 3, 290.00, NULL, '200504'),
(5, 'Cepillo de dientes ', 18, 20.00, NULL, '8154581000330'),
(6, 'Set de bolsas con dispensador ', 1, 100.00, NULL, '7502313359026'),
(7, 'Peluche ratón sin sonido 5461', 2, 50.00, NULL, '7503040254615'),
(8, 'Juguete para gato bolas 3 250425', 2, 50.00, NULL, '7504350175256'),
(9, 'Hueso peluche con sonido', 1, 50.00, NULL, '7500311748460'),
(10, 'Churú sabores variados', 12, 30.00, NULL, '850030015549'),
(11, 'Cepillo para baño con compartimiento para shampoo ', 1, 100.00, NULL, '6941055136846'),
(12, 'Traje de Chimuelo talla 2', 1, 150.00, NULL, '200505'),
(13, 'Buster Rompevientos gris morado XXL ', 1, 413.00, NULL, '5703188304148'),
(14, 'Buster Abrigo Gris Verde M', 1, 432.00, NULL, '5703188304469'),
(15, 'Buster Rompevientos Gris y Verde M', 1, 334.00, NULL, '5703188304193'),
(16, 'Buster Impermeable Negro M/L  ', 1, 671.00, NULL, '5703188286154'),
(17, 'Correa delgada de 2 mts', 1, 170.00, NULL, '200506'),
(18, 'Rollo de desechos Individual ', 18, 15.00, NULL, '200507'),
(19, 'Peluche Pez', 2, 50.00, NULL, '888556216645'),
(20, 'Peluche dinosaurio', 1, 50.00, NULL, '6945926304914'),
(21, 'Set de peluchitos chiles', 2, 50.00, NULL, '888556216713'),
(22, 'Cepillo para mascota de hule', 3, 50.00, NULL, '7504307905103'),
(23, 'Pelota de picos PE31574', 2, 50.00, NULL, '6945926304303'),
(24, 'Aro de plástico PE31574', 2, 50.00, NULL, '6945926304303'),
(25, 'Lanzador de Pelotas ', 2, 50.00, NULL, '888556207612'),
(26, 'Porta bolsa para desechos', 3, 50.00, NULL, '6977547564361'),
(27, 'Juguete cascabel', 2, 50.00, NULL, '6945926304303'),
(28, 'Hueso hule', 2, 50.00, NULL, '6945926304303'),
(29, 'Pelota con estuche', 3, 50.00, NULL, '7504311515480'),
(30, 'Set de cepillos de dientes dedales', 2, 50.00, NULL, '7504317568237'),
(31, 'Dedal Induvidual', 8, 15.00, NULL, '');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `servicios`
--

CREATE TABLE `servicios` (
  `id` int(11) NOT NULL,
  `nombre` varchar(100) DEFAULT NULL,
  `precio` decimal(10,2) DEFAULT NULL,
  `descripcion` text DEFAULT NULL,
  `duracion_min` int(11) DEFAULT NULL,
  `codigo_barras` varchar(100) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_spanish2_ci;

--
-- Volcado de datos para la tabla `servicios`
--

INSERT INTO `servicios` (`id`, `nombre`, `precio`, `descripcion`, `duracion_min`, `codigo_barras`) VALUES
(15, 'Baño raza Pequeña pelo corto ', 180.00, 'Baño raza pequeña pelo corto hasta 22 cm de alto', NULL, '1001201'),
(16, 'Baño raza Pequeña pelo corto ', 200.00, 'Baño raza pequeña con pelo corto pasando los 22 cm hasta 26 cm', NULL, '1001202'),
(17, 'Baño raza Mediana pelo corto', 230.00, 'Baños raza Mediana pelo corto desde 23 cm hasta los 30 cm ', NULL, '1001203'),
(18, 'Baño raza Mediana pelo corto', 280.00, 'Baño raza Mediana pelo corto desde 30 cm hasta 35 cm ', NULL, '1001204'),
(19, 'Baño raza Mediana pelo corto', 300.00, 'Baño raza Mediana pelo corto desde 35 cm hasta 42 cm ', NULL, '1001205'),
(20, 'Baño raza Mediana pelo corto', 350.00, 'Baño raza Mediana pelo corto desde 45 cm hasta 50 cm ', NULL, '1001206'),
(21, 'Baño raza Grande pelo corto', 380.00, 'Baño raza Grande pelo corto desde 51 cm hasta 58 cm ', NULL, '1001207'),
(22, 'Baño raza Grande pelo corto', 450.00, 'Baño raza Grandes pelo corto desde 58 cm hasta 65 cm ', NULL, '1001208'),
(23, 'Baño raza Extra Grande pelo corto', 520.00, 'Baño raza Extra Grande pelo corto desde 65 cm hasta 76 cm', NULL, '1001209'),
(24, 'Baño raza Extra Grande pelo corto', 610.00, 'Baño raza Extra Grande pelo corto desde 76 cm en adelante', NULL, '10012010'),
(25, 'Baño Raza Pequeña Pelo Largo', 200.00, 'Baño Raza Pequeña Pelo Largo hasta 22 cm ', NULL, '1002201'),
(26, 'Baño Raza Pequeña Pelo Largo', 230.00, 'Baño Raza Pequeña Pelo Largo desde 23 cm hasta 28 cm ', NULL, '1002202'),
(27, 'Baño Raza Mediana Pelo Largo', 260.00, 'Baño de Raza Mediana Pelo Largo desde 23 cm hasta 30 cm ', NULL, '1002203'),
(28, 'Baño Raza Mediana Pelo Largo', 280.00, 'Baño Raza Mediana Pelo Largo desde 30 cm hasta 40 cm', NULL, '1002204'),
(29, 'Baño Raza Mediana Pelo Largo', 380.00, 'Baño Raza Mediana Pelo Largo desde 40 cm hasta 50 cm ', NULL, '1002205'),
(30, 'Baño Raza Grande Pelo Largo', 420.00, 'Baño Raza Grande Pelo Largo desde 50 cm hasta 55 cm', NULL, '1002206'),
(31, 'Baño Raza Grande Pelo Largo', 500.00, 'Baño Raza Grande Pelo Largo desde 60 cm hasta 65 cm', NULL, '1002207'),
(32, 'Baño Raza Extra Grande Pelo Largo', 620.00, 'Baño Raza Extra Grande Pelo Largo desde 65 cm hasta 68 cm \r\n', NULL, '1002208'),
(33, 'Baño Raza Extra Grande Pelo Largo', 730.00, 'Baño Raza Extra Grande Pelo Largo desde 65 cm en adelante', NULL, '1002209'),
(34, 'Corte y Baño Raza Pequeña', 280.00, 'Corte y Baño Raza Pequeña hasta 22 cm ', NULL, '1003201'),
(35, 'Corte y Baño Raza Pequeña', 300.00, 'Corte y Baño Raza Pequeña desde 23 cm hasta 25 cm ', NULL, '1003202'),
(36, 'Corte y Baño Raza Mediana ', 320.00, 'Corte y Baño Raza Mediana desde 25 cm hasta 30 cm ', NULL, '1003203'),
(37, 'Corte y Baño Raza Mediana ', 350.00, 'Corte y Baño Raza Mediana desde 30cm hasta 38 cm', NULL, '1003204'),
(38, 'Corte y Baño Raza Mediana ', 380.00, 'Corte y Baño Raza Mediana desde 38 cm hasta 45 cm ', NULL, '1003205'),
(39, 'Corte y Baño Raza Mediana ', 420.00, 'Corte y Baño Raza Mediana desde 43 cm hasta 50 cm ', NULL, '1003206'),
(40, 'Corte y Baño Razas Grandes', 490.00, 'Corte y Baño Razas Grandes desde 50 cm hasta 57 cm ', NULL, '1003207'),
(41, 'Corte y Baño Razas Grandes', 580.00, 'Corte y Baño Razas Grandes desde 57cm hasta 65 cm ', NULL, '1003208'),
(42, 'Corte y Baño Raza Extra Grande ', 680.00, 'Corte y Baño Raza Extra Grande desde 65 cm hasta 72 cm ', NULL, '1003209'),
(43, 'Corte y Baño Raza Extra Grande ', 750.00, 'Corte y Baño Raza Extra Grande desde ', NULL, '10032010'),
(44, 'Corte y Baño Raza Extra Grande ', 810.00, 'Corte de Raza Extra Grande 75 cm en adelante', NULL, '1003209'),
(45, 'Extra nudos', 30.00, 'Se cobra por 20 min extra de servicio por cepillado ', NULL, '1004201'),
(46, 'Pelo muerto', 40.00, 'Se cobra por 20 min extra de servicio por cepillado ', NULL, '1004202'),
(47, 'Spa Hidratación ', 100.00, 'Se le pone sin Bañera de Ozono mascarilla de Artero ', NULL, '1005201'),
(49, 'Spa Hidratación con Ozono ', 150.00, 'Se le pone Mascarilla de Artero con tina de Ozono y se deja por 15 min ', NULL, '1005202'),
(50, 'Spa Keratina con Ozono', 150.00, 'Se le coloca mascarilla de Artero en la tina con Ozono por 15 min ', NULL, '1005203'),
(51, 'Spa Keratina y Planchado ', 130.00, 'Se le coloca Mascarilla de Keratina y se Plancha con protector ', NULL, '1005204'),
(52, 'Spa Detox', 150.00, 'Se le coloca Mascarilla Detox con tina de Ozono', NULL, '1005205'),
(53, 'Pulgas y Garrapatas', 30.00, 'Jabón Antipulgas y garrapatas se deja actuar por 10 min', NULL, '1004203'),
(54, 'Corte de uñas ', 50.00, 'Corte de uñas pequeños y medianos ', NULL, '1004204'),
(55, 'Corte de uñas Grande', 60.00, 'Perros de Raza Grande y Extragrande', NULL, '1004205'),
(56, 'Colorimetría 1 ', 30.00, 'Colorimetria de Agua para una parte del cuerpo ', NULL, '1006201'),
(57, 'Colorimetría 2', 80.00, 'Colorimetría semipermanente en una parte del cuerpo', NULL, '1006202'),
(58, 'Baño para gatos Ch y Md', 400.00, 'Servicio para Gatos de tamaño chico y mediano ', NULL, '1007201'),
(59, 'Baño y Corte para Gatos Ch y Md', 480.00, 'Servicio para gatos Ch y Md incluye corte', NULL, '1007202'),
(60, 'Pelo muerto 1', 10.00, 'Extra de tiempo 10 min\r\n', NULL, '1004206'),
(61, 'Nudos 1', 10.00, 'Tiempo extra 10 min', NULL, '1004206');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `usuarios`
--

CREATE TABLE `usuarios` (
  `id` int(11) NOT NULL,
  `username` varchar(50) DEFAULT NULL,
  `PASSWORD` varchar(50) DEFAULT NULL,
  `rol` varchar(20) DEFAULT 'empleado'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_spanish2_ci;

--
-- Volcado de datos para la tabla `usuarios`
--

INSERT INTO `usuarios` (`id`, `username`, `PASSWORD`, `rol`) VALUES
(1, 'Lomitos.admin', 'Lomitos.9224!', 'admin'),
(2, 'Empleado1', 'Lomitos123', 'empleado'),
(3, 'emmanuel_admon@sistemasjj.com.mx', 'Emanuel.2025!', 'admin');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `ventas`
--

CREATE TABLE `ventas` (
  `id` int(11) NOT NULL,
  `fecha` timestamp NOT NULL DEFAULT current_timestamp(),
  `total` decimal(10,2) DEFAULT NULL,
  `metodo_pago` varchar(50) DEFAULT NULL,
  `estado` varchar(20) DEFAULT 'activa',
  `cliente_id` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_spanish2_ci;

--
-- Volcado de datos para la tabla `ventas`
--

INSERT INTO `ventas` (`id`, `fecha`, `total`, `metodo_pago`, `estado`, `cliente_id`) VALUES
(4, '2026-02-28 09:42:24', 100.00, 'Efectivo', 'cancelada', NULL),
(5, '2026-02-28 22:41:37', 50.00, 'Efectivo', 'cancelada', NULL),
(6, '2026-03-01 02:52:32', 565.00, 'Efectivo', 'cancelada', NULL),
(7, '2026-03-01 03:05:06', 180.00, 'Efectivo', 'cancelada', NULL),
(8, '2026-03-03 11:15:02', 230.00, 'Efectivo', 'cancelada', NULL),
(9, '2026-03-03 13:25:34', 300.00, 'Tarjeta', 'cancelada', 3),
(10, '2026-03-14 17:29:13', 250.00, 'Efectivo', 'cancelada', 4),
(11, '2026-03-14 18:13:25', 320.00, 'Efectivo', 'cancelada', 5),
(12, '2026-03-22 05:39:55', 280.00, 'Transferencia', 'cancelada', 3),
(13, '2026-03-22 05:49:14', 280.00, 'Efectivo', 'cancelada', 3);

--
-- Índices para tablas volcadas
--

--
-- Indices de la tabla `caja`
--
ALTER TABLE `caja`
  ADD PRIMARY KEY (`id`);

--
-- Indices de la tabla `citas`
--
ALTER TABLE `citas`
  ADD PRIMARY KEY (`id`),
  ADD KEY `mascota_id` (`mascota_id`),
  ADD KEY `servicio_id` (`servicio_id`);

--
-- Indices de la tabla `clientes`
--
ALTER TABLE `clientes`
  ADD PRIMARY KEY (`id`);

--
-- Indices de la tabla `corte_caja`
--
ALTER TABLE `corte_caja`
  ADD PRIMARY KEY (`id`);

--
-- Indices de la tabla `detalle_venta`
--
ALTER TABLE `detalle_venta`
  ADD PRIMARY KEY (`id`),
  ADD KEY `venta_id` (`venta_id`);

--
-- Indices de la tabla `entradas_inventario`
--
ALTER TABLE `entradas_inventario`
  ADD PRIMARY KEY (`id`),
  ADD KEY `producto_id` (`producto_id`);

--
-- Indices de la tabla `gastos_fijos`
--
ALTER TABLE `gastos_fijos`
  ADD PRIMARY KEY (`id`);

--
-- Indices de la tabla `insumos`
--
ALTER TABLE `insumos`
  ADD PRIMARY KEY (`id`);

--
-- Indices de la tabla `mascotas`
--
ALTER TABLE `mascotas`
  ADD PRIMARY KEY (`id`),
  ADD KEY `cliente_id` (`cliente_id`);

--
-- Indices de la tabla `productos`
--
ALTER TABLE `productos`
  ADD PRIMARY KEY (`id`);

--
-- Indices de la tabla `servicios`
--
ALTER TABLE `servicios`
  ADD PRIMARY KEY (`id`);

--
-- Indices de la tabla `usuarios`
--
ALTER TABLE `usuarios`
  ADD PRIMARY KEY (`id`);

--
-- Indices de la tabla `ventas`
--
ALTER TABLE `ventas`
  ADD PRIMARY KEY (`id`),
  ADD KEY `fk_cliente_venta` (`cliente_id`);

--
-- AUTO_INCREMENT de las tablas volcadas
--

--
-- AUTO_INCREMENT de la tabla `caja`
--
ALTER TABLE `caja`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=10;

--
-- AUTO_INCREMENT de la tabla `citas`
--
ALTER TABLE `citas`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=12;

--
-- AUTO_INCREMENT de la tabla `clientes`
--
ALTER TABLE `clientes`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=6;

--
-- AUTO_INCREMENT de la tabla `corte_caja`
--
ALTER TABLE `corte_caja`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=9;

--
-- AUTO_INCREMENT de la tabla `detalle_venta`
--
ALTER TABLE `detalle_venta`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=24;

--
-- AUTO_INCREMENT de la tabla `entradas_inventario`
--
ALTER TABLE `entradas_inventario`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=6;

--
-- AUTO_INCREMENT de la tabla `gastos_fijos`
--
ALTER TABLE `gastos_fijos`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT de la tabla `insumos`
--
ALTER TABLE `insumos`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT de la tabla `mascotas`
--
ALTER TABLE `mascotas`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=12;

--
-- AUTO_INCREMENT de la tabla `productos`
--
ALTER TABLE `productos`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=32;

--
-- AUTO_INCREMENT de la tabla `servicios`
--
ALTER TABLE `servicios`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=63;

--
-- AUTO_INCREMENT de la tabla `usuarios`
--
ALTER TABLE `usuarios`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT de la tabla `ventas`
--
ALTER TABLE `ventas`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=14;

--
-- Restricciones para tablas volcadas
--

--
-- Filtros para la tabla `citas`
--
ALTER TABLE `citas`
  ADD CONSTRAINT `citas_ibfk_1` FOREIGN KEY (`mascota_id`) REFERENCES `mascotas` (`id`),
  ADD CONSTRAINT `citas_ibfk_2` FOREIGN KEY (`servicio_id`) REFERENCES `servicios` (`id`);

--
-- Filtros para la tabla `detalle_venta`
--
ALTER TABLE `detalle_venta`
  ADD CONSTRAINT `detalle_venta_ibfk_1` FOREIGN KEY (`venta_id`) REFERENCES `ventas` (`id`);

--
-- Filtros para la tabla `entradas_inventario`
--
ALTER TABLE `entradas_inventario`
  ADD CONSTRAINT `entradas_inventario_ibfk_1` FOREIGN KEY (`producto_id`) REFERENCES `productos` (`id`);

--
-- Filtros para la tabla `mascotas`
--
ALTER TABLE `mascotas`
  ADD CONSTRAINT `mascotas_ibfk_1` FOREIGN KEY (`cliente_id`) REFERENCES `clientes` (`id`);

--
-- Filtros para la tabla `ventas`
--
ALTER TABLE `ventas`
  ADD CONSTRAINT `fk_cliente_venta` FOREIGN KEY (`cliente_id`) REFERENCES `clientes` (`id`) ON DELETE SET NULL;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
