# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

bl_info= {
	"name": "Import HardReset Models",
	"author": "Mr. Wonko",
	"version": (0, 1),
	"blender": (2, 5, 9),
	"api": 39307,
	"location": "File > Import > HardReset Model (.meta)",
	"description": "Imports Hard Reset .meta/.rhm models",
	"warning": "",
	"category": "Import-Export"}
	
import bpy, os, struct

# helper function to read next char from file
def peek(file):
	c = file.read(1)
	if c != "":
		#file.seek(-1, 1) # 1 back (-1) from current position (1 == SEEK_CUR) - does not work for files -.-
		file.seek(file.tell() - 1) # 1 back from current position - this is more verbose anyway
	return c

# '[key] = [value]' -> '[key]', '[value]'
def toKeyValue(line):
	# split at =
	key, value = line.split("=", 1)
	if not value:
		return
	# prettify, return
	return key.strip(), value

# '"string"' -> True, 'string'
def toString(s):
	s = s.strip()
	if s[:1] != '"' or s[-1:] != '"':
		return False
	return True, s[1:-1]

def toColor(s):
	s = s.strip()
	if s[:1] != '(' or s[-1:] != ')':
		return False, [0, 0, 0]
	s = s[1:-1]
	values = s.split(",")
	if len(values) < 3:
		return False, [0, 0, 0]
	return True, [float(values[0]), float(values[1]), float(values[2])]

UnhandlesChunkKeys = []
# a chunk will translate into a mesh/object pair in Blender.
class Chunk:
	def __init__(self):
		self.message = ""
		self.startIndex = -1 # first (triangle) index belonging to this chunk
		self.primCount = -1 # amount of (triangle) indices belonging to this chunk
		self.baseIndex = None # ???
		self.diffuse = "" # diffuse texture
		self.specular = "" # specular texture
		self.normal = "" # normal map texture
		self.vColor = [1, 1, 1] # vertex colour
		self.material = "" # material, for physics (esp. electricity) I guess
		# todo: add more!
	
	def loadFromFile(self, file):
		if file.readline().strip("\n") != "[Chunk]":
			self.message = "Expected chunk definition in file did not start with [Chunk]!"
			return False
		# read 
		numChunks = -1
		
		#read lines while there are any interesting ones
		while peek(file) not in ["[", ""]: # next definition, EOF
			# read line
			line = file.readline()
			
			if line == "\n": # empty line
				continue
			line = line.strip("\n")
			# split at =
			key, value = toKeyValue(line)
			if not key:
				self.message = "line without ="
				return False
			#   use
			
			# mesh information
			if key == "StartIndex":
				self.startIndex  = int(value)
				continue
			if key == "PrimCount":
				self.primCount = int(value)
				continue
			if key == "BaseIndex":
				self.baseIndex = int(value)
				continue
			
			# material, basically
			if key == "Diffuse":
				self.diffuse = toString(value)
				continue
			if key == "Specular":
				self.specular = toString(value)
				continue
			if key == "Normal":
				self.normal = toString(value)
				continue
			if key == "vColor":
				self.material = toColor(value)
				continue
			
			# physics
			if key == "Material":
				self.material = toString(value)
				continue
			
			# bounds
			if key == "Bounds":
				# I don't need them bounds
				continue
				# todo: add more
				"""
				
				fBaseUVTile = 1.000000
				fLayerUVTile = 1.000000
				fWrapAroundTerm = 1.000000
				
				fSpecularMultiplier = 4.000000
				fSpecularPowerMultiplier = 20.000000
				fEnvMultiplier = 1.000000
				fEmissiveMultiplier = 1.000000
				"""
			
			# unhandled key?
			if key not in UnhandlesChunkKeys: # only warn once
				print("Info: Unhandled Chunk Key \"%s\"" % (key))
				UnhandlesMeshKeys.append(key)
				continue
		if self.startIndex == -1:
			self.message = "No StartIndex defined!"
			return False
		if self.primCount == -1:
			self.message = "No PrimCount defined!"
			return False
		return True
	
	def toBlender(self, vertices, indices, chunkIndex, mesh):
		return True

UnhandlesMeshKeys = []
# more like a group of mesh objects, though they may possibly contain only one (or none?)
class Mesh:
	def __init__(self):
		self.message = ""
		self.chunks = []
		self.name = ""
		self.childNum = 0 # not sure what this is
	
	def loadFromFile(self, file):
		if file.readline().strip("\n") != "[Mesh]":
			self.message = "Mesh definition in file did not start with [Mesh]!"
			return False
		# read 
		chunkCount = -1
		
		#read lines while there are any interesting ones
		while peek(file) not in ["[", ""]: # next definition, EOF
			# read line
			line = file.readline()
			
			if line == "\n": # empty line - should not happen?
				continue
			line = line.strip("\n")
			# split at =
			key, value = toKeyValue(line)
			if not key:
				self.message = "line without ="
				return False
			#   use
			
			# use
			if key == "ChunkCount":
				chunkCount = int(value)
				continue
			if key == "ChunkStart":
				chunkStart = int(value)
				if chunkStart != 0:
					self.message = "chunkStart is %d, not 0. I don't know what that means, except that I probably can't read this file properly." % (chunkStart)
					return False
				continue
			if key == "Name":
				success, self.Name = toString(value)
				if not success:
					self.message = "Name is no string"
					return False
				continue
			if key == "ChildNum":
				self.childNum = int(value)
				continue
			if key == "Bounds":
				# I don't need to read bounds - I just have to save 'em.
				continue
			# unhandled key?
			if key not in UnhandlesMeshKeys: # only warn once
				print("Info: Unhandled Mesh Key \"%s\"" % (key))
				UnhandlesMeshKeys.append(key)
				continue
		if chunkCount == -1:
			self.message = "No ChunkCount defined!"
			return False
		for i in range(chunkCount):
			chunk = Chunk()
			if not chunk.loadFromFile(file):
				self.message = "Error reading Chunk %d: %s" % (i, chunk.message)
				return False
			self.chunks.append(chunk)
		return True
	
	def toBlender(self, vertices, indices):
		for index, chunk in enumerate(self.chunks):
			if not chunk.toBlender(vertices, indices, index, self):
				return False
		return True

class Vertex:
	def __init__(self):
		self.position = [0, 0, 0]
		# what are the other values saved?
	
	def loadFromFile(self, file):
		bindata = file.read(32) # a vertex is 32 bytes long.
		if len(bindata) < 32:
			return False, "Unexpected End of File"
		data = struct.unpack("3f20x", bindata) # 3 floats and 20 unknown bytes
		for i in range(3):
			self.position[i] = data[i]
		return True, ""

unhandledGeometryKeys = []
class HRImporter:
	def __init__(self):	
		self.message = ""
		self.numVertices = -1
		self.numIndices = -1
		self.meshes = []
		self.vertices = [] # Vertex
		self.indices = () # all the indices, not grouped
	
	def loadModel(self, filepath):
		# strip extension
		pathWithoutExtension, extension = os.path.splitext(filepath)
		# is this a .meta file?
		if extension != ".meta":
			# no! we don't like that.
			self.message = "No .meta file!"
			return False
		
		# load .meta file - header
		if not self.loadMeta(filepath):
			return False
		
		# load .rhm file - vertices/triangles
		if not self.loadRhm(pathWithoutExtension + ".rhm"):
			return False
		
		# write gathered information to blender
		if not self.toBlender():
			return False
		
		# if we got here, it can only mean one thing: Success!
		return True
	
	def loadMeta(self, filepath):
		with open(filepath, "r") as file:
			# most common error
			self.message = "Invalid/unsupported file (see console for details)"
			if file.readline().strip("\n") != "[Geometry]":
				print(".meta file does not start with [Geometry]" % line)
				return False
			numMeshes = -1
			
			while peek(file) not in ["[", ""]:
				line = file.readline()
				if line == "\n":
					continue
				line = line.strip("\n")
				# split at =
				key, value = toKeyValue(line)
				if not key:
					self.message = "line without ="
					return False
				#   use
				if key == "Meshes":
					numMeshes = int(value)
					continue
				if key == "Vertices":
					self.numVertices = int(value)
					continue
				if key == "Indices":
					self.numIndices = int(value)
					continue
				# unhandled key?
				if key not in unhandledGeometryKeys: # only warn once
					print("Info: Unhandled Geometry Key \"%s\"" % (key))
					unhandledGeometryKeys.append(key)
					continue
			
			# read meshes
			for i in range(numMeshes):
				mesh = Mesh()
				if not mesh.loadFromFile(file):
					print("Error reading mesh %d:\n%s" % (i, Mesh.message))
					return False
				self.meshes.append(mesh)
			
			# there's nothing else in the file, as far as I know.
			return True
		self.message = "Could not open " + filepath
		return False
	
	def loadRhm(self, filepath):
		with open(filepath, "rb") as file:
			# more indices than can be indexed with a 2 byte unsigned short?
			if self.numVertices > pow(2, 16):
				print("Warning: More than %d vertices, some cannot be indexed!" % pow(2, 16))
				# ignore them?
			
			# read vertices
			for i in range(self.numVertices):
				v = Vertex()
				success, message = v.loadFromFile(file)
				if not success:
					self.message = "Error reading vertex %d: %s" % (i, message)
					return False
				self.vertices.append(v)
			print("Read %d vertices" % self.numVertices)
			
			# read triangles
			bindata = file.read(2*self.numIndices)
			if len(bindata) < 2*self.numIndices:
				self.message = "Error reading indices: Unexpected end of file!"
				return False
			self.indices = struct.unpack("%dH" % self.numIndices, bindata) # 3 unsigned shorts (2 byte - only up to 65536 vertices!)
			print("Read %d indices" % self.numIndices)
			
			# read check sum
			checksumBin = file.read(4)
			if len(checksumBin) < 4:
				self.message = "Error reading checksum: Unexpected end of file!"
				return False
			checksum = struct.unpack("i", checksumBin)
			print("Checksum (?): %d" % checksum)
			
			# file should be over now
			if len(file.read(1)) != 0:
				self.message = "Rhm file longer than expected!"
				return False
			
			return True
		self.message = "Could not open " + filepath
		return False
	
	def toBlender(self):
		# Before adding any meshes or armatures go into Object mode.
		if bpy.ops.object.mode_set.poll():
			bpy.ops.object.mode_set(mode='OBJECT')
		for mesh in self.meshes:
			if not mesh.toBlender(self.vertices, self.indices):
				self.message = mesh.message
				return False
		return True

from bpy.props import StringProperty, BoolProperty

#  Operator - automatically registered on creation.
class IMPORT_HR_META(bpy.types.Operator):
		'''Import Hard Reset Meta Model Operator.'''
		bl_idname = "import_scene_hardreset.meta"
		bl_label = "Import Hard Reset Model (.meta)"
		bl_description = "Imports a Hard Reset .meta/.rhm pair."
		bl_options = {'REGISTER', 'UNDO'}

		filepath = StringProperty(name="File Path", description="Filepath used for importing the Hard Reset file", maxlen=1024, default="")

		def execute(self, context):
			importer = HRImporter()
			if not importer.loadModel(self.filepath):
				self.report({'ERROR'}, importer.message)
			return {'FINISHED'}

		def invoke(self, context, event):
			wm= context.window_manager
			wm.fileselect_add(self)
			return {'RUNNING_MODAL'}

# callback when menu entry is selected
def menu_callback(self, context):
	# calls the operator
	self.layout.operator(IMPORT_HR_META.bl_idname, text="Hard Reset Model (.meta)")

# called when module is registered
def register():
	bpy.utils.register_module(__name__)
	# add menu entry
	bpy.types.INFO_MT_file_import.append(menu_callback)


def unregister():
	bpy.utils.unregister_module(__name__)
	# remove menu entry
	bpy.types.INFO_MT_file_import.remove(menu_callback)

# if this is executed as a file: register it
if __name__ == "__main__":
	register()