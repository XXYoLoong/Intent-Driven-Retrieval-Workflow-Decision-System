# Copyright 2026 Jiacheng Ni
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""rename resource_docs.metadata to chunk_metadata (fix SQLAlchemy reserved name)

Revision ID: 001
Revises:
Create Date: 2026-02-05

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 若表 resource_docs 存在且含 metadata 列，则重命名为 chunk_metadata（避免与 Declarative 保留名冲突）
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        result = conn.execute(
            sa.text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = 'resource_docs' AND column_name = 'metadata'"
            )
        )
        if result.scalar():
            op.alter_column(
                "resource_docs",
                "metadata",
                new_column_name="chunk_metadata",
                existing_type=sa.JSON(),
            )
    else:
        try:
            op.alter_column(
                "resource_docs",
                "metadata",
                new_column_name="chunk_metadata",
                existing_type=sa.JSON(),
            )
        except Exception:
            pass


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        result = conn.execute(
            sa.text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = 'resource_docs' AND column_name = 'chunk_metadata'"
            )
        )
        if result.scalar():
            op.alter_column(
                "resource_docs",
                "chunk_metadata",
                new_column_name="metadata",
                existing_type=sa.JSON(),
            )
    else:
        try:
            op.alter_column(
                "resource_docs",
                "chunk_metadata",
                new_column_name="metadata",
                existing_type=sa.JSON(),
            )
        except Exception:
            pass
