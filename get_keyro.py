import requests
from urllib.parse import quote, urlsplit, urlunsplit

url = "https://procesos.inmovilla.com/portal/kyeroagencias3/3696-kyero-zuH7JCWY%20%20colaboradores.xml?no_third_party_tracking=true"
out_path = "kyero_feed.xml"

parts = urlsplit(url)
safe_path = quote(parts.path, safe="/%")
safe_url = urlunsplit(
    (parts.scheme, parts.netloc, safe_path, parts.query, parts.fragment)
)

with requests.get(safe_url, stream=True, timeout=30) as r:
    r.raise_for_status()
    ct = r.headers.get("Content-Type", "")
    print("Content-Type:", ct)
    with open(out_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

print("Saved to", out_path)
