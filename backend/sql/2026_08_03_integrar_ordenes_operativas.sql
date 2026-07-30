INSERT INTO public.ordenes_estados_historial (
    empresa_id, orden_id, estado_anterior, estado_nuevo, motivo, usuario_id
)
SELECT
    orden.empresa_id,
    orden.id,
    NULL,
    orden.estado,
    'Estado adoptado al habilitar historial',
    orden.created_by
FROM public.ordenes_trabajo AS orden
WHERE NOT EXISTS (
    SELECT 1
    FROM public.ordenes_estados_historial AS historial
    WHERE historial.orden_id = orden.id
);

INSERT INTO public.ordenes_servicios (
    empresa_id, orden_id, servicio_id, descripcion, cantidad,
    precio_unitario, descuento, total, estado
)
SELECT
    item.empresa_id,
    cotizacion.orden_id,
    item.servicio_id,
    item.descripcion,
    item.cantidad,
    item.precio_unitario,
    item.descuento,
    item.total,
    CASE
        WHEN orden.estado IN ('terminada', 'entregada') THEN 'terminado'
        ELSE 'pendiente'
    END
FROM public.cotizaciones_items AS item
JOIN public.cotizaciones AS cotizacion ON cotizacion.id = item.cotizacion_id
JOIN public.ordenes_trabajo AS orden ON orden.id = cotizacion.orden_id
WHERE cotizacion.estado = 'aprobada'
  AND item.tipo = 'servicio'
  AND NOT EXISTS (
      SELECT 1
      FROM public.ordenes_servicios AS existente
      WHERE existente.orden_id = cotizacion.orden_id
  );

CREATE INDEX IF NOT EXISTS idx_ordenes_historial_orden_fecha
    ON public.ordenes_estados_historial (orden_id, created_at);
CREATE INDEX IF NOT EXISTS idx_ordenes_servicios_orden_estado
    ON public.ordenes_servicios (orden_id, estado);
