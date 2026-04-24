# LombardBot

## Operación y manejo de fechas

- **Convención única de almacenamiento:** todas las fechas/horas que se persisten en base de datos se guardan en **UTC**.
- En la capa de persistencia se utiliza `datetime.utcnow()` para registrar timestamps.
- En mensajes de Discord donde aplica visualización para usuarios, las fechas se formatean en la zona deseada (por ejemplo, `Europe/Madrid`).

### Recomendación operativa

- Mantener la BD en UTC para evitar ambigüedades por horario de verano.
- Convertir a la zona de negocio únicamente en la capa de presentación (mensajes, embeds, reportes).
