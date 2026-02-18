#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Uso: $0 <db_name> [odoo_conf_path]"
  echo "Variables opcionales:"
  echo "  WSEM_DRY_RUN=1                 Solo simula cambios"
  echo "  WSEM_WRITE_DEFAULT_CODE=0      No copia el código de barras a default_code"
  echo "  WSEM_COMMIT=1                  Fuerza commit al final (por defecto: activado)"
  echo "  WSEM_COMPANY_ID=<id>           Filtra por compañía del producto"
  echo "  WSEM_PRODUCT_ID=<id>           Procesa solo un product.product"
  echo "  WSEM_TEMPLATE_ID=<id>          Procesa solo variantes de un product.template"
  echo "  WSEM_DEBUG=1                   Imprime depuración detallada (por defecto: activado, use 0 para desactivar)"
  exit 1
fi

DB_NAME="$1"
ODOO_CONF="${2:-}"

ODOO_CMD=(/opt/odoo18/odoo/odoo-bin shell -d "$DB_NAME")
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
should_commit = _as_bool(os.getenv("WSEM_COMMIT"), default=True)
company_id = _as_int(os.getenv("WSEM_COMPANY_ID"))
product_id = _as_int(os.getenv("WSEM_PRODUCT_ID"))
template_id = _as_int(os.getenv("WSEM_TEMPLATE_ID"))
debug = _as_bool(os.getenv("WSEM_DEBUG"), default=True)

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

if product_id is not None:
    domain.append(("id", "=", product_id))

if template_id is not None:
    domain.append(("product_tmpl_id", "=", template_id))

processing_model = product_model
if selected_company:
    processing_model = product_model.with_company(selected_company).with_context(allowed_company_ids=[selected_company.id])

products = processing_model.search(domain)
for product in products:
    if debug:
        print("-" * 80)
        print(f"[DEBUG] product.id={product.id} product_tmpl_id={product.product_tmpl_id.id}")
        print(f"[DEBUG] product.display_name={product.display_name}")
        print(f"[DEBUG] current barcode={product.barcode!r} default_code={product.default_code!r}")

    expression = processing_model._get_barcode_expression_for_record(product)
    if not expression:
        missing_expression += 1
        if debug:
            print("[DEBUG] skipped: no barcode expression configured for the company")
        continue

    if debug:
        print(f"[DEBUG] expression={expression!r}")

    barcode = processing_model._generate_barcode(product, expression=expression)
    if not barcode:
        errors += 1
        print(f"[ERROR] {product.id}: {product.display_name}")
        if debug:
            print("[DEBUG] barcode generation returned an empty value")
        continue

    if debug:
        print(f"[DEBUG] generated barcode={barcode!r}")

    vals = {"barcode": barcode}
    if write_default_code:
        vals["default_code"] = barcode

    if all(product[field] == value for field, value in vals.items()):
        skipped += 1
        if debug:
            print("[DEBUG] skipped: values already match")
        continue

    if not dry_run:
        product.write(vals)
        updated += 1
        if debug:
            product.flush_recordset(["barcode", "default_code"])
            print(f"[DEBUG] write applied -> barcode={product.barcode!r} default_code={product.default_code!r}")
    elif debug:
        print("[DEBUG] dry-run active: write skipped")

if not dry_run and should_commit:
    env.cr.commit()
    if debug:
        print("[DEBUG] transaction committed")

print("Barcode regeneration summary:")
print(f"- company filter: {company_id if company_id is not None else 'none'}")
print(f"- product filter: {product_id if product_id is not None else 'none'}")
print(f"- template filter: {template_id if template_id is not None else 'none'}")
print(f"- products: {len(products)}")
print(f"- updated: {updated}")
print(f"- skipped: {skipped}")
print(f"- errors : {errors}")
if company_id is not None and not selected_company.codigo_de_barras_por_atributos:
    print(f"- warning: missing barcode expression in company {selected_company.display_name} ({selected_company.id})")
elif missing_expression:
    print(f"- warning: skipped {missing_expression} products without barcode expression configured in their company")
PY
