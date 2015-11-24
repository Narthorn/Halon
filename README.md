Halon.py - Wildstar archive explorer
========

A small python script to view and extract contents of the Wildstar data archives (.index, .archive files in the Patch folder).

Usage
-----


```
python3 halon.py [-rd] archive {find name | list [path] | extract [path] [dest_path] | diff other_archive [path]}

   find: Find all files and folders whose path contains the given name inside the archive.
   list: List the contents of the folder given in path, or the entire archive if no path is given.
extract: Extract from archive the folder given in path, optionally inside the folder given in dest_path.
   diff: Show the removed/added/changed files and folders between two archives.

-r, --recursive : Enable recursing through subfolders (on by default for find and extract).
-d, --debug: Enable extra debugging info on archive and file objects (mostly useful in interactive mode).
```

###### Examples :

```
$ python3 halon.py Wildstar/Patch/ClientData.archive find FloatTextPanel
UI/FloatText/FloatTextPanel.lua
UI/FloatText/FloatTextPanel.xml
```
```
$ python3 halon.py Wildstar/Patch/ClientData.archive list UI/FloatText
UI/FloatText
    FloatText.lua
    FloatTextPanel.lua
    FloatTextPanel.xml
    TestFloatTextForms.xml
    toc.xml
```
```
$ python3 halon.py Wildstar/Patch/ClientData.archive extract UI/FloatText wildstar_ui/
$ ls wildstar_ui/FloatText
FloatText.lua  FloatTextPanel.lua  FloatTextPanel.xml  TestFloatTextForms.xml  toc.xml
```
```
$ python3 halon.py Wildstar.10760/Patch/ClientData.archive diff Wildstar.10894/Patch/ClientData.archive
! UI (1 removed, 1 added, 879 changed)
! Map (212 removed, 86 added, 4304 changed)
! DB (0 removed, 1 added, 124 changed)
! Sky (0 removed, 16 added, 1129 changed)
! EnvMap (0 removed, 0 added, 67 changed)
! Art (0 removed, 9 added, 91 changed)
! Audio (1 removed, 36 added, 24 changed)
```


Python API
----------

```python
import halon

# Open archive file (with or without extension):
client = halon.Filesystem('Wildstar/Patch/Client.index')
clientdata = halon.Filesystem('Wildstar/Patch/ClientData')

# Find named files or directories
for item in clientdata.find('FloatTextPanel'):
	print(item.path)
>>>
UI/FloatText/FloatTextPanel.lua
UI/FloatText/FloatTextPanel.xml

# List contents of a directory
print(clientdata['UI/FloatText'])
>>>
UI/FloatText
	FloatText.lua
	FloatTextPanel.lua
	FloatTextPanel.xml
	TestFloatTextForms.xml
	toc.xml

# Read file contents
toc = clientdata['UI/FloatText/toc.xml'].read() # returns raw bytes
print(toc.decode('ascii'))
>>>
"""
<Addon Name="FloatText" Version="1">
    <Script Name="FloatText.lua" />
    <Script Name="FloatTextPanel.lua" />
    <Form Name="TestFloatTextForms.xml" />
    <Form Name="FloatTextPanel.xml" />
</Addon>
"""

# Extract a directory (with optional destination path)
clientdata['UI/FloatText'].extract('wildstar_files/')
```
