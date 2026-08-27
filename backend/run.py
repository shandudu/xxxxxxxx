import granian

from backend.cli import CustomReloadFilter
from backend.core.conf import settings

if __name__ == '__main__':
    # DEBUG:
    # 如果你喜欢在 IDE 中进行 DEBUG，可在 IDE 中直接右键启动此文件
    # 如果你喜欢通过 print 方式进行调试，建议使用 fba cli 方式启动服务

    # Warning:
    # 如果你正在通过 python 命令启动此文件，请遵循以下事宜：
    # 1. 按照官方文档通过 uv 安装依赖
    # 2. 命令行空间位于 backend 目录下
    host = '127.0.0.1'
    port = 8000
    base_url = f'http://{host}:{port}'

    # 直接从 IDE 启动 run.py 时不会经过 fba CLI，因此在这里补充打印访问地址。
    print(f'API 请求地址: {base_url}{settings.FASTAPI_API_V1_PATH}', flush=True)
    if settings.ENVIRONMENT == 'dev':
        print(f'Swagger 文档: {base_url}{settings.FASTAPI_DOCS_URL}', flush=True)
        print(f'Redoc 文档: {base_url}{settings.FASTAPI_REDOC_URL}', flush=True)
        print(f'OpenAPI JSON: {base_url}{settings.FASTAPI_OPENAPI_URL or ""}', flush=True)

    granian.Granian(
        target='main:app',
        interface='asgi',
        address=host,
        port=port,
        reload=True,
        reload_filter=CustomReloadFilter,
    ).serve()
