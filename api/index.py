# Vercel serverless entry point.
# Vercel's Python runtime expects a callable `handler(request, context)`.
# Mangum adapts the FastAPI ASGI app to that interface. Without this,
# the deployment serves nothing (why /docs was empty before).
from mangum import Mangum

from app.main import app

handler = Mangum(app)
