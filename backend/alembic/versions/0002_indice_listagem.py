from pathlib import Path

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[2] / "sql" / "06_indice_listagem.sql"


def upgrade() -> None:
    op.execute(SQL.read_text(encoding="utf8"))


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_products_category_name")
