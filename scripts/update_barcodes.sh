#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Uso: $0 <db_name> [odoo_conf_path]"
  echo "Variables opcionales:"
  echo "  WSEM_DRY_RUN=1                 Solo simula cambios"
  echo "  WSEM_WRITE_DEFAULT_CODE=0      No copia el código de barras a default_code"
  exit 1
fi

DB_NAME="$1"
ODOO_CONF="${2:-}"

ODOO_CMD=(odoo shell -d "$DB_NAME")
if [[ -n "$ODOO_CONF" ]]; then
  ODOO_CMD+=( -c "$ODOO_CONF" )
fi

"${ODOO_CMD[@]}" <<'PY'
import os


def _as_bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


dry_run = _as_bool(os.getenv("WSEM_DRY_RUN"), default=False)
write_default_code = _as_bool(os.getenv("WSEM_WRITE_DEFAULT_CODE"), default=True)

product_model = env["product.product"]
expression = env["ir.config_parameter"].sudo().get_param("wsem_pos.codigo_de_barras_por_atributos")

updated = 0
skipped = 0
errors = 0

if not expression:
    print("Barcode regeneration summary:")
    print("- updated: 0")
    print("- skipped: 0")
    print("- errors : 0")
    print("- warning: missing barcode expression in parameter wsem_pos.codigo_de_barras_por_atributos")
else:
    for product in product_model.search([]):
        barcode = product_model._generate_barcode(product)
        if not barcode:
            errors += 1
            print(f"[ERROR] {product.id}: {product.display_name}")
            continue

        vals = {"barcode": barcode}
        if write_default_code:
            vals["default_code"] = barcode

        if all(product[field] == value for field, value in vals.items()):
            skipped += 1
            continue

        if not dry_run:
            product.write(vals)
        updated += 1

    print("Barcode regeneration summary:")
    print(f"- updated: {updated}")
    print(f"- skipped: {skipped}")
    print(f"- errors : {errors}")
PY
