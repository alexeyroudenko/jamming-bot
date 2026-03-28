```
kubectl apply -f deployment.yaml
```

```
kubectl get pods --show-labels
```

# http://tags.jamming-bot.arthew0.online/


# http://html-renderer.jamming-bot.arthew0.online/

```
kubectl port-forward service/html-renderer-service 8080:80
```

```
curl -o ya.ru.png "http://localhost:8080/render?url=https://ya.ru.ru&width=1920&height=1080&dsf=2"
```

```
curl -o ya.ru.png "http://html-renderer.jamming-bot.arthew0.online/render?url=https://ya.ru.ru&width=1920&height=1080&dsf=2"
```

```
curl -o ya.ru.png -H "Host: html-renderer.jamming-bot.arthew0.online" "http://$(hostname -I | awk '{print $1}')/render?url=https://ya.ru&width=1920&height=1080&dsf=2"
```

## CSP / static app (`/static-app/`)

If Chrome reports **Content Security Policy blocks eval**: the nginx image for `frontend-static-app` sets a `Content-Security-Policy` header that includes `script-src ... 'unsafe-eval'` for the bundled JS. If you **also** set CSP at Cloudflare, Traefik, or another proxy, browsers enforce **all** policies—add `'unsafe-eval'` to **that** policy as well, or remove the duplicate CSP so only one source applies.



## Tag visualizations (NLP-driven art)

Full-screen pages are served by **app-service** (Flask), same host paths as `/tags/` and `/tags/3d/`.

| URL | Description |
|-----|-------------|
| [`/tags/constellation/`](https://jamming-bot.arthew0.online/tags/constellation/) | 2D “star field”: force layout, similarity edges from spaCy vectors, co-occurrence edges from live `tags_updated` / `analyzed` bursts |
| [`/tags/vectorfield/`](https://jamming-bot.arthew0.online/tags/vectorfield/) | Three.js particle flow: field from tag embedding directions + noise |
| [`/tags/chaos-attractor/`](https://jamming-bot.arthew0.online/tags/chaos-attractor/) | Lorenz attractor; σ, ρ, β driven by tag-count entropy / variance; shake on new tag bursts |

**UI:** Freeze and **Export PNG** on each page; palette follows `.cursor/STYLE_GUIDE.md` (`static/tags_vis_shared.css` + light scanline overlay on the canvas).

**JSON API:** `POST /api/tags/embeddings/` with body `{"words": ["tag1", ...], "max_words": 48, "min_sim": 0.38, "max_links": 160}` — returns `words`, `vectors2d`, `links` (uses `en_core_web_md` in the app-service image). If the model is missing, the client falls back to co-occurrence / procedural fields.

Navigation links are also added from `/tags/`, `/tags/3d/`, and `/tags/phrases/`.