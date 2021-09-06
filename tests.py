import railway

settings = railway.Settings(
    ipv4_host=railway.LOCALHOST,
    ipv6_host=railway.LOCALHOST,
    port=8000,
    use_ipv6=False,
    ssl_context=None,
    worker_count=3
)

app = railway.Application(settings=settings)