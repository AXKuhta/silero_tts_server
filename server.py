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
		try:
			chunk = sock.recv(1)
		except ConnectionResetError:
			return None

		if chunk == b'\n':
			return str.decode().strip()
		if not chunk:
			return None

		str = str + chunk


device = torch.device("cpu")
torch.set_num_threads(2)
file = "v3_1_ru.pt"

model = torch.package.PackageImporter(file).load_pickle("tts_models", "model")
model.to(device)

MainSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
MainSocket.bind((Host, ListenPort))
MainSocket.listen()

# A wrapper that makes it possible to write .wav into a socket
# You can validate the total number of bytes written by adding a print here
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
		Request = HTTPReadLine(Client)

		if Request == None:
			print("Disconnected")
			break

		Method, URL, Version = Request.split(" ")
		Text = urllib.parse.unquote(URL)[1:]
		print("Synthesize [" + Text + "]")

		# We support Keep-Alive so we have to read all the pending data
		while HTTPReadLine(Client) != '':
			pass

		try:
			audio = model.apply_tts(text=Text, sample_rate=sample_rate, speaker=speaker)

			# In order to do Keep-Alive, having Content-Length is mandatory
			# WAV header will always be 44 bytes, as derived from the source code of the wave module
			# And the audio is 16 bit, so we multiply by 2
			size = 44 + len(audio) * 2
			header = "Content-Length: " + str(size) + "\r\n"

			Client.send(b"HTTP/1.1 200 OK\r\n")
			Client.send(header.encode())
			Client.send(b"\r\n")

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

