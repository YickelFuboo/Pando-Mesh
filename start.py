import sys
import uvicorn
from app.main import app
from app.config.settings import settings

if __name__ == "__main__":
    try:
        uvicorn.run(
            "app.main:app",
            host=settings.service_host,
            port=settings.service_port,
            reload=settings.debug,
            access_log=False,
        )
    except OSError as e:
        if getattr(e, "winerror", None) == 10048 or e.errno == 10048:
            print(
                f"[error] 端口 {settings.service_port} 已被占用。"
                f"请先关闭 run.bat 启动的「Pando-Mesh API」窗口，"
                f"或在 VS Code 中使用带 preLaunchTask 的 Debug 配置。",
                file=sys.stderr,
            )
        raise SystemExit(1) from e
