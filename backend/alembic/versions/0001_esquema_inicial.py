from pathlib import Path

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

SQL_DIR = Path(__file__).resolve().parents[2] / "sql"


def _read(name: str) -> str:
    lines = (SQL_DIR / name).read_text(encoding="utf8").splitlines()
    return "\n".join(l for l in lines if l.strip().upper() not in ("BEGIN;", "COMMIT;"))


def upgrade() -> None:
    for f in ("01_schema.sql", "02_logic.sql", "03_indexes.sql"):
        op.execute(_read(f))


def downgrade() -> None:
    op.execute("""
        DROP VIEW IF EXISTS vw_order_summary;
        DROP PROCEDURE IF EXISTS sp_checkout(UUID, VARCHAR, VARCHAR, UUID);
        DROP TABLE IF EXISTS payments, order_items, orders, inventory, product_images,
                             products, categories, addresses, users CASCADE;
        DROP FUNCTION IF EXISTS fn_check_stock() CASCADE;
        DROP FUNCTION IF EXISTS fn_update_timestamp() CASCADE;
    """)
