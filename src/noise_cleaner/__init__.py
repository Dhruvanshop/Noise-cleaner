# Resilient imports - allow app to start even if some deps are missing
try:
    from .denoise import DenoiseConfig, DenoiseResult, denoise_file
except ImportError as e:
    import logging
    logging.warning(f"Could not import denoise module: {e}")
    DenoiseConfig = DenoiseResult = denoise_file = None

try:
    from .denoise_ai import _AI_AVAILABLE, denoise_file_ai
except ImportError as e:
    import logging
    logging.warning(f"Could not import denoise_ai module: {e}")
    _AI_AVAILABLE = False
    denoise_file_ai = None

try:
    from .server import app, serve
except ImportError as e:
    import logging
    logging.warning(f"Could not import server module: {e}")
    app = serve = None

__all__ = [
    "DenoiseConfig", "DenoiseResult", "denoise_file",
    "_AI_AVAILABLE", "denoise_file_ai",
    "app", "serve",
]
