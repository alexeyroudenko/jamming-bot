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


