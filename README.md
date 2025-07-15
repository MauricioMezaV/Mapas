# Plataforma de asignación automática de zonas de reparto a clientes

Esta plataforma permite asignar automáticamente zonas de reparto a clientes utilizando archivos `.kml` exportados desde Google Maps. A través de la geolocalización de cada cliente, el sistema identifica la zona correspondiente y le asigna sus atributos, generando como resultado un archivo `.xlsx` que contiene tanto los datos del cliente como los de la zona asignada. De esta manera, se elimina la necesidad de modificar manualmente la asignación de cada cliente, facilitando la actualización de zonas de reparto y la visualización de la nueva distribución.

En el futuro, se planea incorporar la funcionalidad de generar capas de clientes y zonas directamente desde archivos `.xlsx`, listas para ser importadas a Google Maps, optimizando aún más el proceso de gestión y visualización.

## Instrucciones de uso

1. **Preparar archivos de entrada:** Exporta desde Google Maps el archivo `.kml` que contiene las zonas de reparto. Asegúrate de contar con la lista de clientes y sus coordenadas geográficas.
2. **Cargar archivos en la plataforma:** Accede a la plataforma. Sube el archivo `.kml`.
3. **Asignación automática:** Ejecuta la función de asignación automática. El sistema analizará la ubicación de cada cliente y le asignará la zona correspondiente, agregando los atributos de la zona a los datos del cliente.
4. **Exportar resultados:** Descarga el archivo `.xlsx` generado, que contendrá la información consolidada de clientes y zonas. Utiliza este archivo para reportes o para futuras importaciones.
5. **Próximas funcionalidades:** Próximamente podrás generar capas de clientes y zonas directamente desde archivos `.xlsx`, listas para ser importadas a Google Maps y facilitar aún más la gestión de la distribución.

Para más detalles, contacta al equipo de operaciones de la sucursal Rancagua.
