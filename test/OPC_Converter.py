#!/usr/bin/python
# -*- coding: UTF-8 -*-
import logging, time, sys, decimal, OpenOPC, ttk, tkFileDialog, urllib,urllib2
import threading
from Tkinter import *
import Tkinter as tk
from datetime import datetime
from opcua import ua, uamethod, Server


logging.basicConfig()
reload(sys)
sys.setdefaultencoding('utf-8') 
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

#实例化window
window = tk.Tk()
window.title('OPC Converter')
window.geometry('800x200')

## 2. Connect to OPC-DA server
c = OpenOPC.client()
# List OPC-DA servers
#servers = c.servers()

#下拉菜单 选择OPC_DA服务器
def getComboBox(*args):
    OPC_DA_SERVER = C1.get()
L1 = tk.Label(window,text='Select a OPC_DA server:', width=30).grid(row = 0, column = 0)
C1 = ttk.Combobox(window,value=(c.servers()), width = 40)
C1.grid(row = 0, column = 1)
C1.bind("<<ComboboxSelected>>",getComboBox)


#配置OPC_UA服务器
def SelectCaPath():
    path_Ca = tkFileDialog.askopenfilename(filetypes=[("der","der")])
    pathCa.set(path_Ca)
def SelectPkPath():
    path_Pk = tkFileDialog.askopenfilename(filetypes=[("pem","pem")])
    pathPk.set(path_Pk)
pathCa = StringVar()
pathPk = StringVar()

# L2 = tk.Label(window, text = 'Set OPC_UA Certificate:', width = 30).grid(row = 1, column = 0)
# E1 = tk.Entry(window, textvariable = pathCa, width = 40).grid(row = 1, column = 1)
# B1 = tk.Button(window, text = 'Select file', command = SelectCaPath).grid(row = 1, column = 2)
# L3 = tk.Label(window, text = 'Set OPC_UA Private_Key:', width = 30).grid(row = 2, column = 0)
# E2 = tk.Entry(window, textvariable = pathPk, width = 40).grid(row = 2, column = 1)
# B2 = tk.Button(window, text = 'Select file', command = SelectPkPath).grid(row = 2, column = 2)
L4 = tk.Label(window, text = 'Set OPC_UA URI:', width = 30).grid(row = 3, column = 0)
default_value_URI = StringVar()
default_value_URI.set('urn:freeopcua:python:server')
E3 = tk.Entry(window, width = 40, textvariable = default_value_URI)
E3.grid(row = 3, column = 1)
L7 = tk.Label(window, text = 'Example: urn:freeopcua:python:server').grid(row = 3, column = 2)
L5 = tk.Label(window, text = 'Set OPC_UA End_Point:', width = 30).grid(row = 4, column = 0)
default_value_EP = StringVar()
default_value_EP.set('opc.tcp://192.168.2.32:48400')
E4 = tk.Entry(window, width = 40, textvariable = default_value_EP)
E4.grid(row = 4, column = 1)
L6 = tk.Label(window, text = 'Example: opc.tcp://192.168.2.32:48400').grid(row = 4, column = 2)

#更新配置
def update(*args):
    OPC_UA_URI = E3.get()
    OPC_UA_Endpoint = E4.get()
B3 = tk.Button(window, text = 'Update', command = update).grid(row = 5, column = 0)

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
		#print('Datachange', opc_da_address, val, cc.write((opc_da_address, val,)))
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


server = None
def start():
    logging.basicConfig()
    OPC_DA_SERVER = C1.get()
    c.connect(OPC_DA_SERVER)
    global server
    if server is None:
       server = Server()
    OPC_UA_Endpoint = E4.get()
    server.set_endpoint(OPC_UA_Endpoint)
    #server.load_certificate(OPC_UA_CERTIFICATE)
    #server.load_private_key(OPC_UA_PRIVATE_KEY)
    OPC_UA_URI = E3.get()
    uri = OPC_UA_URI
    idx = server.register_namespace(uri)
    root = server.nodes.objects.add_object(idx, OPC_DA_SERVER)
    ## 3. Discover OPC-DA server nodes
    server.start()
    readable_variable_handles = {}
    writeable_variable_handles = {}
    tree = {}
    node_obj = {}
    file_track = []
    init_nodes = None
    while True:
        nodes = c.list('*',recursive=True, flat = True)
        if init_nodes is None:
            init_nodes = len(nodes)
        if len(nodes)!= init_nodes:
            print("NODES Changed")
        # 'nodes' is a list of dot-delimited strings.
        #Matriton simulator has BUGs for the following nodes! So remove them if trying to use Matriton simulator
        #nodes.remove(u'Bucket Brigade.Time')
        #nodes.remove(u'Random.Time')
        #nodes.remove(u'Write Error.Time')
        #nodes.remove(u'Write Only.Time')
        
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
                path = '.'.join(folders[0:i]).encode('utf-8')
                if path not in tree.keys():
                    tree[path] = parent.add_folder(idx, folder.encode('utf-8'))
            # 'path' is now the folder that file resides in.
            # Determine node properties
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
            
            if file in file_track:
                pass
            else:
                #print('Adding node ' + file + ' at path ' + path)
                opcua_node = tree[path].add_variable(idx, file.encode('utf-8'), ua.Variant(current_value, ua.VariantType.UInt16))
                #Determine readable vs. writable
                if node_obj[ITEM_ACCESS_RIGHTS] in [ACCESS_READ]:
                    readable_variable_handles[node] = opcua_node
                if node_obj[ITEM_ACCESS_RIGHTS] in [ACCESS_WRITE, ACCESS_READ_WRITE]:
                    opcua_node.set_writable()
                    writeable_variable_handles[node] = opcua_node
                file_track.append(file)
            
            #print "NODES -> %d"%len(nodes)
            #print "TREE -> %d"%len(tree)
            #print "FOLDERS -> %d"%len(folders)


            
            

        #try:
        ## 4. Subscribe to datachanges coming from OPC-UA clients
        handler = SubscriptionHandler(len(writeable_variable_handles))
        sub = server.create_subscription(100, handler)
        sub.subscribe_data_change(writeable_variable_handles.values())
        readables = list(readable_variable_handles.keys())
        time.sleep(5)
        ## 5. Read all readables simultaneously and update the OPC-UA variables
        #while True:
        
        for reading in c.read(readables):
            readables = list(readable_variable_handles.keys())
            opc_da_id = reading[0]
            variable_handle = readable_variable_handles[opc_da_id]
            variable_handle.set_value(read_value(reading[1:]))
        
        #finally:
            #server.stop()
            #c.close()

def thread_start():
    thread = threading.Thread(target=start)
    thread.start()
def thread_end():
    thread = threading.Thread(target=stop)
    thread.start()
#启动转发

B4 = tk.Button(window, text = 'Start', command = thread_start, ).grid(row=5,column=1)


# 关闭转发
def stop():
    window.quit()
    server.stop()
    c.close()
B5 = tk.Button(window, text = 'Stop', command = thread_end).grid(row=5, column=2)


#开启窗口
window.mainloop()
