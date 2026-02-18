# wsem_pos

Códigos de barras para variantes en PoS.

## Regenerar códigos de barras masivamente

Se agregó un script de mantenimiento en `scripts/` para actualizar todos los códigos de barras existentes en base a la expresión configurada en:

- `wsem_pos.codigo_de_barras_por_atributos`

> La carpeta `scripts/` no se instala como datos de Odoo; se deja para tareas operativas desde shell.

### Opción 1: desde shell (recomendada)

El script `scripts/update_barcodes.sh` es autosuficiente y recorre todos los productos en `odoo shell` para recalcular y escribir los códigos de barras masivamente.

```bash
scripts/update_barcodes.sh <db_name> [odoo_conf_path]
```

Variables opcionales:

- `WSEM_DRY_RUN=1`: simula sin escribir.
- `WSEM_WRITE_DEFAULT_CODE=0`: actualiza solo `barcode` y no `default_code`.
- `WSEM_KEEP_DEFAULT_CODE=1`: si `default_code` ya tiene valor, no lo sobrescribe.
- `WSEM_COMMIT=1`: fuerza `commit` al final (activado por defecto, ignorado en dry run).
- `WSEM_COMPANY_ID=<id>`: limita la ejecución a una compañía.
- `WSEM_PRODUCT_ID=<id>`: procesa solo un `product.product`.
- `WSEM_TEMPLATE_ID=<id>`: procesa solo variantes de un `product.template`.
- `WSEM_DEBUG=1`: imprime datos de depuración por producto.

Ejemplo:

```bash
WSEM_DRY_RUN=1 WSEM_DEBUG=1 WSEM_PRODUCT_ID=933 WSEM_TEMPLATE_ID=176 scripts/update_barcodes.sh mi_bd /etc/odoo.conf
```

### Opción 2: durante una instalación/upgrade

No se ejecuta automáticamente para permitir definir primero la expresión de código de barras.
Una vez definida, correr el script anterior para aplicar el cálculo masivo.
