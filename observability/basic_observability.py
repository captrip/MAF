import time
import logging
from functools import wraps
from typing import Callable, Any,Dict

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(module)s - %(filename)s : %(lineno)d - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    )

logger = logging.getLogger("MAF_Logs")

def timed_hook(hook_name: str) -> Callable:
    """Decorator to time the execution of a hook function and log the duration.

    Args:
        hook_name (str): The name of the hook being timed.
        """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            logger.info(f"Starting execution of hook '{hook_name}'.")
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                end_time = time.time()
                duration = end_time - start_time
                logger.info(f"Hook '{hook_name}' executed in {duration:.4f} seconds.")
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            logger.info(f"Starting execution of hook '{hook_name}'.")
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                end_time = time.time()
                duration = end_time - start_time
                logger.info(f"Hook '{hook_name}' executed in {duration:.4f} seconds.")

        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    return decorator