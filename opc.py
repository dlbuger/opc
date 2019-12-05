# Name: opcda_to_opcua.py
#
# Description:
# Proxy between OPC-DA server and OPC-UA client.
# Firstly the OPC-DA namespace is traversed using a recursive
# function. These variables are then classified as readable or writable
# and added to the OPC-UA namespace. The readable variables are read
# periodically from the OPC-DA server and published on the OPC-UA server.
# The writable OPC-UA tags are monitored for changes. When a change is
# caught then the new value is published to the OPC-DA server.
#
# The code is organized as follows:
# 1. Configuration
# 2. Connec to OPC-DA server
# 3. Discover OPC-DA server nodes
# 4. Subscribe to datachanges coming from OPC-UA clients
# 5. Read all readables simultaneously and update the OPC-UA variables
#    to reflect the OPC-DA readings

# Requires Anaconda, OpenOPC
# L 609 in address_space.py, python-opcua v 0.90.3

import logging, time, sys, decimal, OpenOPC
from datetime import datetime
from opcua import ua, uamethod, Server

## 1. Configuration
OPC_DA_SERVER = 'S7200.OPCServer'
OPC_UA_CERTIFICATE = 'certificate.der'
OPC_UA_PRIVATE_KEY = 'private_key.pem'
OPC_UA_URI = 'http://dtu.dk'

# Constants
ITEM_ID_VIRTUAL_PROPERTY = 0
ITEM_CANONICAL_DATATYPE = 1
ITEM_VALUE = 2
ITEM_QUALITY = 3
ITEM_TIMESTAMP = 4
ITEM_ACCESS_RIGHTS = 5
SERVER_SCAN_RATE = 6
ITEM_EU_TYPE = 7
ITEM_EU_INFO = 8
ITEM_DESCRIPTION = 101
ACCESS_READ = 0
ACCESS_WRITE = 1
ACCESS_READ_WRITE = 2

# Set up server
server = Server()
server.set_endpoint('opc.tcp://kt-pr-4tank:4840/four_tank_process/')
server.load_certificate(OPC_UA_CERTIFICATE)
server.load_private_key(OPC_UA_PRIVATE_KEY)
uri = OPC_UA_URI
idx = server.register_namespace(uri)
root = server.nodes.objects.add_object(idx, OPC_DA_SERVER)

## 2. Connect to OPC-DA server
c = OpenOPC.client()
# List OPC-DA servers
#servers = c.servers()
c.connect(OPC_DA_SERVER)

class SubscriptionHandler(object):
	def __init__(self,n):
		self.i = 0
		self.n = n
	def final_datachange_notification(self, node, val, data):
		path_as_string = node.get_path_as_string()
		# 'path_as_string' is a list of strings containing:
		# 0: 0:Root
		# 1: 1:Objects
		# 2: 2:OPC DA Server
		# 3 and onwards: 3:[Step of path to node in OPC-DA]
		opc_da_address = '.'.join([a.split(':')[1] for a in path_as_string[3:]])
		cc = OpenOPC.client()
		cc.connect(OPC_DA_SERVER)
		print('Datachange', opc_da_address, val, cc.write((opc_da_address, val,)))
		cc.close()
	# This function is called initially to catch the notifications from newly added nodes
	def datachange_notification(self, node, val, data):
		self.i = self.i + 1
		#print('Catching meaningless datachange notification')
		if self.i == self.n:
			#print('Finished catching meaningless datachange notifications')
			self.datachange_notification = self.final_datachange_notification

def read_value(value):
	value = value[0]
	if isinstance(value,decimal.Decimal):
		value = float(value)
	elif isinstance(value,list):
		if len(value) == 0:
			value = None
	elif isinstance(value,tuple):
		if len(value) == 0:
			value = None
	return value

## 3. Discover OPC-DA server nodes
readable_variable_handles = {}
writeable_variable_handles = {}
nodes = c.list('*',recursive=True)
# 'nodes' is a list of dot-delimited strings.
tree = {}
for node in nodes:
	parts = node.split('.')
	# Folders are the steps on the path to the file.
	folders = parts[:-1]
	file = parts[-1]
	# Create folder tree if it does not already exist
	for i, folder in enumerate(folders,1):
		if i == 1:
			parent = root
		else:
			parent = tree[path]
		path = '.'.join(folders[0:i])
		if path not in tree.keys():
			tree[path] = parent.add_folder(idx,folder)
	# 'path' is now the folder that file resides in.
	# Determine node properties
	node_obj = {}
	for id, description_of_id, value in c.properties(node):
		if id is ITEM_ACCESS_RIGHTS:
			if value == 'Read':
				value = ACCESS_READ
			elif value == 'Write':
				value = ACCESS_WRITE
			elif value == 'Read/Write':
				value = ACCESS_READ_WRITE
		node_obj[id] = value
	current_value = read_value((node_obj[ITEM_VALUE],))
	if type(current_value) != int:
		current_value = 0
	#print('Adding node '+file+' at path '+path)
	opcua_node = tree[path].add_variable(idx, file, ua.Variant(current_value, ua.VariantType.UInt16))
	# Determine readable vs. writable
	if node_obj[ITEM_ACCESS_RIGHTS] in [ACCESS_READ]:
		readable_variable_handles[node] = opcua_node
	if node_obj[ITEM_ACCESS_RIGHTS] in [ACCESS_WRITE, ACCESS_READ_WRITE]:
		opcua_node.set_writable()
		writeable_variable_handles[node] = opcua_node

try:
	server.start()
	## 4. Subscribe to datachanges coming from OPC-UA clients
	handler = SubscriptionHandler(len(writeable_variable_handles))
	sub = server.create_subscription(100, handler).subscribe_data_change(writeable_variable_handles.values())
	readables = list(readable_variable_handles.keys())
	while True:
		time.sleep(0.5)
		## 5. Read all readables simultaneously and update the OPC-UA variables
		for reading in c.read(readables):
			opc_da_id = reading[0]
			variable_handle = readable_variable_handles[opc_da_id]
			variable_handle.set_value(read_value(reading[1:]))
finally:
	server.stop()
	c.close()