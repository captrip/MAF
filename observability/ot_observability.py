import aysncio
import uuid
import contextvars
import inspect
import functools

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource

resource = Resource.create({"service.name": "MAF-Service"})
provider = TracerProvider(resource=resource)
trace.set_tracer_provider(provider)

trace_file = open("observability/trace.log", "a",encoding="utf-8")
file_console_exporter = ConsoleSpanExporter(out=trace_file)

provider.add_span_processor(BatchSpanProcessor(file_console_exporter))
tracer = trace.get_tracer(__name__)

request_id_ctx = contextvars.ContextVar("request_id", default=None)

def get_request_id() -> str:
    request_id = request_id_ctx.get()
    if request_id is None:
        request_id = str(uuid.uuid4())
        request_id_ctx.set(request_id)
    return request_id

def _safe_repr(value: Any,maxlen = 200) -> str:
    try:
        s = repr(value)
    except Exception:
        s = f"<unrepresentable value of type {type(value).__name__}>"
    if len(s) > maxlen:
        s = s[:maxlen] + "...(truncated)"
    return s

def traced(span_name: str = None,*,with_args: bool = False) -> Callable:
    def decorator(func):
        name = span_name or getattr(func, "__qualname__", func.__name__)

        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                request_id = get_request_id()
                with tracer.start_as_current_span(name) as span:
                    span.set_attribute("request.id", request_id)
                    span.set_attribute("function.name", func.__name__)
                    span.set_attribute("function.qualname", getattr(func,"__qualname__",func.__name__))
                    span.set_attribute("code.filepath",getattr(func,"__code__",None).co_filename if hasattr(func,"__code__") else "")
                    span.set_attribute("code.lineno",getattr(func,"__code__",None).co_firstlineno if hasattr(func,"__code__") else -1)

                    if with_args:
                        span.set_attribute("function.args", _safe_repr(args))
                        span.set_attribute("function.kwargs", _safe_repr(kwargs))
                    try:
                        result = await func(*args, **kwargs)
                        return result
                    except Exception as e:
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        raise
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                request_id = get_request_id()
                with tracer.start_as_current_span(name) as span:
                    span.set_attribute("request.id", request_id)
                    span.set_attribute("function.name", func.__name__)
                    span.set_attribute("function.qualname", getattr(func,"__qualname__",func.__name__))
                    span.set_attribute("code.filepath",getattr(func,"__code__",None).co_filename if hasattr(func,"__code__") else "")
                    span.set_attribute("code.lineno",getattr(func,"__code__",None).co_firstlineno if hasattr(func,"__code__") else -1)

                    if with_args:
                        span.set_attribute("function.args", _safe_repr(args))
                        span.set_attribute("function.kwargs", _safe_repr(kwargs))
                    try:
                        result = func(*args, **kwargs)
                        return result
                    except Exception as e:
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        raise
            return sync_wrapper
    return decorator
        