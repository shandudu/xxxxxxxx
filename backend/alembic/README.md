# Database migrations

Alembic is the only supported way to upgrade the schema of an existing
database. Run migrations from the repository root:

```powershell
.\.venv\Scripts\fba.exe alembic current
.\.venv\Scripts\fba.exe alembic upgrade
```

`fba init` is only for creating or rebuilding a disposable, empty development
database. It calls SQLAlchemy `drop_all()` and must never be used as an upgrade
command for an existing database.

## One-time baseline for an existing database

Databases created before Alembic tracking may contain all baseline tables but
have no `alembic_version` table. After taking a backup and verifying that the
baseline schema already exists, stamp it once and then run the upgrade:

```powershell
.\.venv\Scripts\alembic.exe stamp c822e1392fbf
.\.venv\Scripts\fba.exe alembic upgrade
```

Do not stamp an empty or partially initialized database. Stamping records a
version without executing that version's schema operations.

The MES/ERP legacy cleanup revision `8f3c9a7d2b11` removes only
`mes_operation.default_work_center_id` and its attached foreign key. It does
not remove any other physical foreign keys.
