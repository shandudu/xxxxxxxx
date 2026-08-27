"""Check that ERP/MES and monitoring API operations require authentication."""

from __future__ import annotations

from backend.core.registrar import register_app


def main() -> int:
    paths = register_app().openapi().get('paths', {})
    business_operations = 0
    missing_security: list[str] = []
    for path, path_item in paths.items():
        if not (path.startswith('/api/v1/erp') or path.startswith('/api/v1/mes') or path == '/api/v1/monitors/alerts'):
            continue
        for method, operation in path_item.items():
            if method.upper() not in {'GET', 'POST', 'PUT', 'PATCH', 'DELETE'}:
                continue
            business_operations += 1
            if not operation.get('security'):
                missing_security.append(f'{method.upper()} {path}')

    if missing_security:
        for item in missing_security:
            print(f'ERROR: unauthenticated business route: {item}')
        return 1
    print(f'OK: authenticated ERP/MES/alert operations ({business_operations})')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
