import torch
import socket
import urllib.parse
import array
import wave

# TCP Server configuration
ListenPort = 8021
Host = ''

def HTTPReadLine(sock):
	str = b""

	while True:
		chunk = sock.recv(1)
		if chunk == b'\n':
			return str.decode().strip()

		str = str + chunk

device = torch.device("cpu")
torch.set_num_threads(2)
file = "ru_v3.pt"

model = torch.package.PackageImporter(file).load_pickle("tts_models", "model")
model.to(device)

MainSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
MainSocket.bind((Host, ListenPort))
MainSocket.listen()

# A wrapper that makes it possible to write .wav into a socket
# Switch back to io.BytesIO(bstring) if this breaks
class wrapsock():
	def __init__(self, sock):
		self.sock = sock

	def write(self, data):
		self.sock.sendall(data)

	def flush(self):
		pass # Pray

# Removes dependency on numpy
def tensor_to_int16array(tensor):
	return array.array("h", tensor.to(dtype=torch.int16))

# Options
# Sample rate: [8000, 24000, 48000]
# Speakers: ["aidar", "baya", "kseniya", "xenia", "random"]
sample_rate = 48000
speaker = "xenia"

while True:
	print("Waiting for connections...")
	Client, Addr = MainSocket.accept()
	print("New connection!")

	while Client:
		Method, URL, Version = HTTPReadLine(Client).split(" ")
		Text = urllib.parse.unquote(URL)[1:]
		print("Synthesize [" + Text + "]")

		# No Keep-Alive without Content-Length
		# while HTTPReadLine(Client) != '':
		#	pass

		try:
			audio = model.apply_tts(text=Text, sample_rate=sample_rate, speaker=speaker)

			Client.send(b"HTTP/1.1 200 OK\r\n\r\n")
			#Client.send(Text.encode())

			ws = wrapsock(Client)

			wf = wave.open(ws, "wb")
			wf.setnchannels(1)
			wf.setsampwidth(2)
			wf.setframerate(sample_rate)
			wf.writeframes( tensor_to_int16array(audio*32767) )
			wf.close()
		except BrokenPipeError:
			print("Abrupt disconnect")
			break
		except (ValueError, Exception):
			print("Failed to synthesize that!")
			Client.send(b"HTTP/1.1 500 Internal server error\r\n\r\n")


		# Send FIN packet
		# Let client close the connection
		Client.shutdown(2)
		break
