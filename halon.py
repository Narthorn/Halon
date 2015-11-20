#!/usr/bin/env python3

import struct
import codecs
import os.path
import lzma
import contextlib

@contextlib.contextmanager
def optopen(*args):
	try:
		with open(*args) as f:
			yield f
	except FileNotFoundError:
		yield None

class Filesystem:
	def __init__(self, basepath):

		self.basepath,_ = os.path.splitext(basepath)

		with open(self.basepath + '.index',   'rb') as index, \
		  optopen(self.basepath + '.archive', 'rb') as data:

			self.index = Archive(index)
			self.data = Archive(data) if data else None

			self.root = Directory('', None, self, self.index.root_dir_index)

			self.find = self.root.find
			self.extract = self.root.extract

	def __getitem__(self, path=None):
		return self.root[path]

class Archive:
	def __init__(self, file):

		self.debug = {}
		self.file = file
		self.name = file.name
		self.fs = None

		header = struct.Struct('<4sI512xQQQIII')
		magic,version,filesize,unk1,fs_offset,fs_count,unk2,root_index = header.unpack(file.read(header.size))

		if debug:
			self.debug['name'] = self.name
			self.debug['magic'] = magic
			self.debug['version'] = version
			self.debug['filesize'] = filesize
			self.debug['fs_count'] = fs_count
			self.debug['unknowns'] = [unk1, unk2]

		file.seek(fs_offset)
		self.fs = [struct.unpack('<QQ', file.read(16)) for _ in range(fs_count)]

		offset, blocksize = self.fs[root_index]

		file.seek(offset)
		magic,version,*rest = struct.unpack('<4sIII', file.read(16))

		if magic == b'CRAA':
			block_count, block_table_index = rest 
			offset, blocksize = self.fs[block_table_index]
			file.seek(offset)
			self.blocks = {}
			for _ in range(block_count):
				index, sha1, size = struct.unpack('<I20sQ', file.read(32))
				self.blocks[sha1] = (index, size)

		if magic == b'XDIA':
			aidx_unk1, self.root_dir_index = rest

			if debug:
				self.debug['unknowns'].append(aidx_unk1)

	def __str__(self):
		return (
		"Archive {name}:\n"
		"	Magic: {magic}\n"
		"	Version: {version}\n"
		"	Filesize: {filesize} bytes\n"
		"	Number of filesystem entries: {fs_count}\n"
		"	Unknowns: {unknowns}"
		).format(**self.debug) if debug else super().__str__()

	def __repr__(self):
		return "<Archive('%s')>" % self.name


class Directory:
	def __init__(self, name, parent, fs, block_index):
		
		self.name = name
		self.path = os.path.join(parent and parent.path or '', name)
		self.parent = parent
		self.fs = fs 
		self.block_index = block_index
		self.dirs = {}
		self.files = {}

		index_file = fs.index.file
		block_offset, block_size = fs.index.fs[block_index]

		index_file.seek(block_offset)

		ndirs, nfiles = struct.unpack('<II', index_file.read(8))
		dir_entries = [struct.unpack('<II', index_file.read(8)) for _ in range(ndirs)]
		file_entries = [struct.unpack('<II8sQQ20s4x', index_file.read(56)) for _ in range(nfiles)] 

		remaining = block_size - (index_file.tell() - block_offset)
		names = index_file.read(remaining)

		for name_offset, block_index in dir_entries:
			name = names[name_offset:names.index(b'\0', name_offset)].decode('ascii')
			self.dirs[name] = Directory(name, self, fs, block_index)

		for name_offset, *filedata in file_entries:
			name = names[name_offset:names.index(b'\0', name_offset)].decode('ascii')
			self.files[name] = File(name, self, fs, *filedata)

	def find(self, path='', recursive=True):
		for file in self.files.values():
			if path in file.path:
				yield file
		for dir in self.dirs.values():
			if path in dir.path:
				yield dir
			if recursive:
				yield from dir.find(path)

	def list(self, path='', recursive=False):
		for item in self.find(path, recursive):
			yield item.path

	def extract(self, basepath='', recursive=True):
		subdir = os.path.join(basepath,self.name)
		os.makedirs(subdir)
		for file in self.files.values():
			file.extract(subdir)
		if recursive:
			for dir in self.dirs.values():
				dir.extract(subdir)

	def __getitem__(self, path=None):
		if not path:
			return self

		head,*tail = os.path.normpath(path).split(os.sep,1)
		try:
			if head in self.dirs:
				return self.dirs[head].__getitem__(*tail)
			if head in self.files:
				return self.files[head]
		
			e = FileNotFoundError("Could not find %s" % head)
			e.file = head
			raise e

		except FileNotFoundError as e:
			if path != e.file:
				e.args = ("Could not find %s in path %s" % (e.file,path),)
			raise
	
	def __str__(self):
		return self.path + "\n" + "\n".join("\t%s" % item for i in (sorted(self.dirs),sorted(self.files)) for item in i)

	def __repr__(self):
		return "<Directory('%s', %d)>" % (self.path, self.block_index)
	

class File:
	def __init__(self, name, parent, fs, *filedata):
		self.compression, unk1, self.uncompressed_size, self.compressed_size, self.sha1  = filedata

		self.debug = {}
		self.name = name
		self.path = os.path.join(parent.path or '', name)
		self.fs = fs

		if debug:
			self.debug["compression"] = self.compression
			self.debug["uncompressed"] = self.uncompressed_size
			self.debug["compressed"] = self.compressed_size
			self.debug["sha1"] = codecs.encode(self.sha1, 'hex')
			self.debug["unknowns"] = codecs.encode(unk1, 'hex') 

	def read(self):
		if self.fs.data:
			data = self.fs.data	
			index, filesize = data.blocks[self.sha1]
			offset, blocksize = data.fs[index]
			with open(data.name, 'rb') as archive_file:
				archive_file.seek(offset)
				contents = archive_file.read(blocksize)

			if self.compression == 1: # no compression
				return contents
			elif self.compression == 3: # old compression format 
				raise NotImplemented("Compression type 3 (deflate) not implemented")
			elif self.compression == 5: # weird lzma 
				return lzma.LZMADecompressor().decompress(contents[:5] + struct.pack('<Q', self.uncompressed_size) + contents[5:])
		else:
			raise FileNotFoundError("No %s.archive file." % os.path.basename(self.fs.basepath))

	def extract(self, basepath=''):
		with open(os.path.join(basepath,self.name),'wb') as out:
			out.write(self.read())

	def __str__(self):
		return (
		"File {path}:\n"
		"	Compression type: {compression}\n"
		"	Uncompressed size: {uncompressed} bytes\n"
		"	Compressed size: {compressed} bytes\n"
		"	SHA1 hash: {sha1}\n"
		"	Unknowns: {unknowns}"
		).format(path=self.path, **self.debug) if debug else super().__str__()
	
	def __repr__(self):
		return "<File('%s')>" % self.name

debug = None

if __name__ == "__main__":
	import argparse

	parser = argparse.ArgumentParser(description="Explore and extract directories and files inside Wildstar archive files.")
	parser.add_argument('archive')
	parser.add_argument('command', choices=['find','list','extract'])
	parser.add_argument('path', nargs='?', default='')
	parser.add_argument('dest_path', nargs='?', default='')

	parser.add_argument('--debug', '-d', action="store_true")
	parser.add_argument('--recursive', '-r', action="store_true")

	args = parser.parse_args()

	debug = args.debug

	archive = Filesystem(args.archive)

	if args.command == 'find':
		for item in archive.find(args.path):
			print(item.path)

	elif args.command == 'list':
		if args.recursive:
			for item in archive[args.path].find():
				print(item.path)
		else:
			print(archive[args.path])

	elif args.command == 'extract':
		archive[args.path].extract(args.dest_path)
