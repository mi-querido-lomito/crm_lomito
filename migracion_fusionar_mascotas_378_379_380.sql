-- Fusiona los registros duplicados 379 y 380 en el registro 378.
-- Antes de ejecutar: confirma que los tres IDs corresponden a la misma
-- mascota y realiza un respaldo de la base de datos.
--
-- La migración conserva las citas y ventas: solo cambia su mascota_id al 378.
-- Ejecuta este archivo completo en una sola sesión de MySQL/phpMyAdmin.

START TRANSACTION;

-- Verificación previa: deben aparecer los tres IDs y corresponder a la
-- mascota que se desea fusionar.
SELECT id, cliente_id, nombre, especie, raza, edad
FROM mascotas
WHERE id IN (378, 379, 380)
ORDER BY id;

-- Historial que será conservado bajo la mascota #378.
UPDATE citas
SET mascota_id = 378
WHERE mascota_id IN (379, 380);

UPDATE ventas
SET mascota_id = 378
WHERE mascota_id IN (379, 380);

UPDATE detalle_venta
SET mascota_id = 378
WHERE mascota_id IN (379, 380);

-- Solo después de transferir todas las referencias se eliminan los duplicados.
DELETE FROM mascotas
WHERE id IN (379, 380);

-- Comprobación dentro de la misma transacción: debe quedar solo el #378.
SELECT id, cliente_id, nombre, especie, raza, edad
FROM mascotas
WHERE id IN (378, 379, 380)
ORDER BY id;

COMMIT;
