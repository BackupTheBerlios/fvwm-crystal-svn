#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 
# This file is part of FVWM - Crystal.
# 
# FVWM - Crystal is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# FVWM - Crystal is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with Pyslide; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import os
import sys
import random
import optparse
import traceback
from xml.dom import minidom
from mimetypes import guess_type
from xml.dom.ext import PrettyPrint

# I don't know if it will speed up script, why don't try.
try: 
	import psyco
	psyco.full()
except:
	pass


__name__ = "wal"
__author__ = "Łukasz Strzygowski <lucass@gentoo.pl>"
__version__ = "0.1-pre6"

def parseArgv(argv):
	""" Parse command line options. Try to expanduser paths """
	
	parser = optparse.OptionParser(version = '%s %s' % (__name__, __version__))
	
	parser.add_option('--last', action = 'store_true', 
		help = 'load last wallpaper')
	parser.add_option('--next', action = 'store_true', 
		help = 'load next wallpaper')
	parser.add_option('--previous', action = 'store_true', 
		help = 'load previous wallpaper')
	parser.add_option('--random', action = 'store_true', 
		help = 'load random wallpaper')
	parser.add_option('--number', action = 'store', type = 'int', 
		help = 'load <number>th wallpaper')
	parser.add_option('--file', action = 'store', default = '',
		help = 'load wallpaper from file')
	parser.add_option('--add', action = 'store', default = '',
		help = 'add wallpapers to database')
	parser.add_option('--remove', action = 'store', default = '',
		help = 'remove wallpapers from database')
	parser.add_option('--remove-current', action = 'store_true', 
		help = 'remove current wallpaper from database')
	parser.add_option('--clear', action = 'store_true', 
		help = 'clear database')
	parser.add_option('--export', action = 'store_true', 
		help = 'export database')
	parser.add_option('--debug', action = 'store_true', 
		help = 'turn debug mode on')
	parser.add_option('--tool', action = 'store', 
		help = 'select tool')
	parser.add_option('--external-tool', action = 'store', metavar='PATH',
		help = 'give full command for tool outside database')
	
	parser.add_option('--config', action = 'store', default = '~/.walrc', 
		help = 'select configuration file')
		
	(options, args) = parser.parse_args(argv)
	
	options.config = os.path.expanduser(options.config)
	options.add = os.path.expanduser(options.add)
	options.remove = os.path.expanduser(options.remove)
	options.file = os.path.expanduser(options.file)
	
	return options

class ParseError(Exception): pass

def loadConfiguration(path):
	""" Load configuration from file. """

	assert(os.path.exists(path))
	
	try:
		document = minidom.parse(path)
		cfgNode = document.getElementsByTagName('config')[0]
		wlpNode = cfgNode.getElementsByTagName('wallpapers')[0]
		wallpapers = [item.firstChild.nodeValue for \
			item in wlpNode.getElementsByTagName('item')]
		currentWal = int(wlpNode.getAttribute('current'))
		toolNode = cfgNode.getElementsByTagName('tools')[0]
		tools = [item.firstChild.nodeValue for item \
			in toolNode.getElementsByTagName('item')]
		defaultTool = toolNode.getAttribute('default')
	except:
		raise ParseError, 'Cannot parse configuration file. Run with --debug for additional informations'

	return {'wallpapers': wallpapers, 'currentWal': currentWal, 
		'tools': tools, 'defaultTool': defaultTool}

def createConfiguration():
	""" Create empty configuration. """

	tools = ['hsetroot -fill FILENAME', 
		'habak -i FILENAME -S',
		'Esetroot FILENAME']

	try:
		defTool = [tool.split()[0] for tool in tools if not \
			os.system('which %s &>/dev/null' % tool.split()[0])][0]
	except:
		raise ParseError, 'Cannot find any usable tool to set wallpaper'
		
	return {'wallpapers': [], 'currentWal': 0, 'tools': tools, 'defaultTool': defTool}

def saveConfiguration(config, path):
	""" Save configuration to file. """
	
	document = minidom.Document()
	cfgNode = document.createElement('config')
	document.appendChild(cfgNode)
	wlpNode = document.createElement('wallpapers')
	wlpNode.setAttribute('current', str(config['currentWal']))
	for wal in config['wallpapers']:
		item = document.createElement('item')
		item.appendChild(document.createTextNode(wal))
		wlpNode.appendChild(item)
	cfgNode.appendChild(wlpNode)
	toolNode = document.createElement('tools')
	toolNode.setAttribute('default', config['defaultTool'])
	for tool in config['tools']:
		item = document.createElement('item')
		item.appendChild(document.createTextNode(tool))
		toolNode.appendChild(item)
	cfgNode.appendChild(toolNode)
	PrettyPrint(document, open(path, 'w'))


class ActionError(Exception): pass

def makeWallpapersList(path):
	""" Do a wallpaper list: from directory, file with list and from image. """
	
	walFormats = ['image/jpeg', 'image/png']

	if os.path.isdir(path):
		fileList = []
		for root, dirs, files in os.walk(path):
			for fileName in files: fileList.append(os.path.join(root, fileName))
		return fileList

	if guess_type(path)[0] in walFormats:
		return [path]
		
	try:
		return [path[:-1] for path in open(path).readlines() \
			if guess_type(path)[0] in walFormats]
	except:
		raise ActionError, 'Cannot open selected file'

		
def doAction(options, config):
	""" Do specified in options action and return modified config """
	
	if options.external_tool:
		tool = options.external_tool
	else:
		try:
			tool = [tool for tool in config['tools'] if \
			tool.split()[0] == (options.tool or config['defaultTool'])][0]
		except:
			raise ParseError, 'Cannot find specified tool in database'

	if options.export:
		for wal in config['wallpapers']: print wal
		return config

	if options.add:
		if not os.path.exists(options.add):
			raise ActionError, 'File doesn\'t exist'
			
		fileList = makeWallpapersList(options.add)

		for fileName in fileList:
			if not fileName in config['wallpapers']:
				config['wallpapers'].append(fileName)
				
		return config

	if options.remove_current:
		options.remove = config['currentWal']
		
	if not options.remove is None and options.remove != '':
		try:
			path = config['wallpapers'][int(options.remove)]
		except IndexError:
			raise ActionError, 'No such wallpaper in database.'
		except ValueError:
			if not os.path.exists(path):
				raise ActionError, 'File doesn\'t exist'
				
		fileList = makeWallpapersList(path)
		for fileName in fileList:
			config['wallpapers'].remove(fileName)
		return config

	if options.clear:
		config['wallpapers'] = []
		config['currentWal'] = 0
		return config

	if options.file:
		os.system(tool.replace('FILENAME', options.file))
		return config

	if not config['wallpapers']:
		raise ActionError, 'The wallpapers database is empty. Use --add option to add images.'	
		
	if options.number:
		if options.number < len(config['wallpapers']):
			config['currentWal'] = options.number
		else:
			raise ActionError, 'No such wallpaper in database.'
	
	if options.next:
		if len(config['wallpapers']) - 1 > config['currentWal']:
			config['currentWal'] += 1
		else:
			config['currentWal'] = 0

	if options.previous:
		if config['currentWal'] > 0:
			config['currentWal'] -= 1
		else:
			config['currentWal'] = len(config['wallpapers']) - 1

	if options.random:
		config['currentWal'] = random.randrange(len(config['wallpapers']))

	if config['currentWal'] >= len(config['wallpapers']):
		raise ActionError, 'Selected wallpaper not in database'

	os.system(tool.replace('FILENAME', config['wallpapers'][config['currentWal']]))
	
	return config
	
def main(argv = sys.argv):
	""" Parse args, load config, perform action, save config """
	options = parseArgv(argv)

	try:
		if not os.path.exists(options.config):
			config = createConfiguration()
		else:
			config = loadConfiguration(options.config)
	
		config = doAction(options, config)
		saveConfiguration(config, options.config)
	except:
		if options.debug: traceback.print_exc()
		sys.stderr.write('\x1b[31;01m * Error: \x1b[0m%s\n' % sys.exc_info()[1])


main()
		

