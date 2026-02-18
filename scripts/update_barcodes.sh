#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Uso: $0 <db_name> [odoo_conf_path]"
  echo "Variables opcionales:"
  echo "  WSEM_DRY_RUN=1                 Solo simula cambios"
  echo "  WSEM_WRITE_DEFAULT_CODE=0      No copia el código de barras a default_code"
  echo "  WSEM_COMPANY_ID=<id>           Filtra por compañía del producto"
  exit 1
fi

DB_NAME="$1"
ODOO_CONF="${2:-}"

ODOO_CMD=(odoo shell -d "$DB_NAME")
if [[ -n "$ODOO_CONF" ]]; then
  ODOO_CMD+=( -c "$ODOO_CONF" )
fi
ODOO_CMD+=( --no-http )

"${ODOO_CMD[@]}" <<'PY'
import os


def _as_bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _as_int(value):
    if value in (None, ""):
        return None
    raw = str(value).strip()
    if not raw.isdigit():
        raise ValueError("WSEM_COMPANY_ID must be numeric")
    return int(raw)


dry_run = _as_bool(os.getenv("WSEM_DRY_RUN"), default=False)
write_default_code = _as_bool(os.getenv("WSEM_WRITE_DEFAULT_CODE"), default=True)
company_id = _as_int(os.getenv("WSEM_COMPANY_ID"))

product_model = env["product.product"]
company_model = env["res.company"]

updated = 0
skipped = 0
errors = 0
missing_expression = 0

domain = []
selected_company = None
if company_id is not None:
    selected_company = company_model.browse(company_id).exists()
    if not selected_company:
        raise ValueError(f"WSEM_COMPANY_ID={company_id} does not exist")
    domain.append(("company_id", "=", company_id))

processing_model = product_model
if selected_company:
    processing_model = product_model.with_company(selected_company).with_context(allowed_company_ids=[selected_company.id])

products = processing_model.search(domain)
for product in products:
    expression = processing_model._get_barcode_expression_for_record(product)
    if not expression:
        missing_expression += 1
        continue

    barcode = processing_model._generate_barcode(product, expression=expression)
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
print(f"- company filter: {company_id if company_id is not None else 'none'}")
print(f"- products: {len(products)}")
print(f"- updated: {updated}")
print(f"- skipped: {skipped}")
print(f"- errors : {errors}")
if company_id is not None and not selected_company.codigo_de_barras_por_atributos:
    print(f"- warning: missing barcode expression in company {selected_company.display_name} ({selected_company.id})")
elif missing_expression:
    print(f"- warning: skipped {missing_expression} products without barcode expression configured in their company")
PY
