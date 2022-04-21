# About silero_tts_server
Bare minimum of code to interact with [Silero TTS models](https://github.com/snakers4/silero-models) over network

The only dependency:

```
pip3 install torch
```

# Usage
Send a GET request and get back a .wav file:

```html
<audio controls src="http://192.168.1.100:8021/Тестовый текст!"></audio>
```
