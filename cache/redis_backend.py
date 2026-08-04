import json

from redis import Redis


class RedisCacheBackend:
    def __init__(self, client: Redis):
        self.client = client
        self.hits = 0
        self.misses = 0

    def get(self, key):
        value = self.client.get(f"cache:{key}")
        if value is None:
            self.misses += 1
            return None
        self.hits += 1
        return json.loads(value)

    def set(self, key, value, ttl_seconds, tags):
        pipe = self.client.pipeline()
        pipe.setex(f"cache:{key}", ttl_seconds, json.dumps(value))
        for tag in tags:
            pipe.sadd(f"cache-tag:{tag}", key)
            pipe.expire(f"cache-tag:{tag}", ttl_seconds)
        pipe.execute()

    def delete(self, key):
        return bool(self.client.delete(f"cache:{key}"))

    def invalidate_tag(self, tag):
        tag_key = f"cache-tag:{tag}"
        keys = self.client.smembers(tag_key)
        if keys:
            self.client.delete(
                *(f"cache:{k.decode() if isinstance(k, bytes) else k}" for k in keys)
            )
        self.client.delete(tag_key)
        return len(keys)

    def stats(self):
        return {
            "hits": self.hits,
            "misses": self.misses,
            "keys": int(self.client.dbsize()),
            "tags": 0,
        }
