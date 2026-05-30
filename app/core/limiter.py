from slowapi import Limiter
from slowapi.util import get_remote_address

# Dùng IP của client làm key
limiter = Limiter(key_func=get_remote_address)