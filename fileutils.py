from contextlib import contextmanager, suppress

@contextmanager
def optopen(*args):
	try:
		with open(*args) as f:
			yield f
	except FileNotFoundError:
		yield None

def peek(file, offset=0, size=None):
	with open(file, 'rb') as data:
		data.seek(offset)
		return data.read(size)

def same_prefix(*str):
	return all(l.count(l[0]) == len(l) for l in zip(*str))

if __name__ == '__main__':
	import os

	def optopen_test(path):
		with optopen(path, 'r') as file:
			if file:
				return file.read()

	with open('blar', 'x') as file:
		file.write('test')
		
	assert optopen_test('blar') == 'test'
	assert optopen_test('blur') == None

	os.remove('blar')
