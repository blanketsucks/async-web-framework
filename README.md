# Subway

The web framework that's going to change your life. Probably.

## Callback Order

```
on_request -> request middlewares -> websocket request? | no -> request callback -> response middlewares -> after_request.
                                                        | yes -> on_websocket -> request callback.
```