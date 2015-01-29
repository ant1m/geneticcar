#!/usr/bin/env python
# encoding=UTF-8
# 
# pylint: disable=W0312,W0301,W0105,W0710,W0612,W0702

VERSION = "1.4.0"

'''
CHANGELOG
v1.4.0
* ADD : Ajout d'une option --log pour extraire les logs du serveur tomcat en cas d'erreur sur un contexte.

v1.3.0
* UPDATE : Affichage de l'aide complète lorsqu'aucun paramètre n'est spécifié.
* FIX : Vérifie l'existence des fichiers avant de tenter de les transférer à l'IHM.
* ADD : [Livraison] Ajout de l'option -c (--comment) pour spécifier un commentaire à la livraison.
* ADD : [Administration] Possibilité d'importer la configuration XML d'un module ou d'une application.

v1.2.2
* UPDATE : Le ChangeLog est désormais stocké dans le script.

v1.2.1
* UPDATE : Compatibilité python 2.4.

v1.2.0
* REMOVE : l'option --type est désormais obsolète, le type est déduit du nom du module.

v1.1.3
* UPDATE : l'option --baseurl est positionnée à http://deploy.ipp93.cvf/ par défaut si rien n'est spécifié.
* ADD : Affiche la liste des actions possibles dans l'aide + complément sur l'aide.
* FIX : problème de locale selon les environnements d'éxécution.
* FIX : Coquille dans le code, qui passait systématiquement le module "ing-webapp" en paramètre de suivi des commandes.

v1.1.0
* FIX : retourne un status != 0 en cas d'erreur
* UPDATE : refactorisation du code + ajout de commentaires

v1.0.1
* 1ère version publique.
'''

import locale
import sys
import os
import time
try:
	from cStringIO import StringIO
except ImportError:
	from StringIO import StringIO
try:
	import pycurl
except ImportError:
	print "Dependency error : python-curl is required"
	sys.exit(1)
from xml.dom import minidom
from optparse import OptionParser

def getText(node):
	# Extract text from an xml node
	nodelist = node.childNodes
	rc = ""
	for node in nodelist:
		if node.nodeType == node.TEXT_NODE:
			rc = rc + node.data
	return rc.encode('utf-8')

   
def getNode(root, nodeName):
	# Get the first node corresponding to "nodeName" from a root node
	return root.getElementsByTagName(nodeName)[0]

class ResultException:
	def __init__(self, message):
		self.message = message
		
	def getMessage(self):
		# The message representing the exception 
		return self.message
	
class CommandResult(object):
	# This result will be used for the response of a webservice call
	def __init__(self, done, status, xml):
		self.done = done
		self.status = status
		self.xml = xml
		
	def isDone(self):
		# Whereas the webservice indicates the command is done or not
		return self.done
	
	def getStatus(self):
		# The command status code (only useful when the command is done) 
		return self.status
	
	def getXml(self):
		# Returns the xml node instance of the response
		return self.xml
	
	def report(self):
		return "Status = %d" % self.getStatus()

class Action:
	# Base class for a webservice action
	def __init__(self, deployer):
		self.deployer = deployer
		self.checkArgs()
	def checkArgs(self):
		# Validates extra arguments for the action
		pass	
	def getInternalModuleName(self):
		# Returns the module name used for this action on the deployment server
		raise ResultException("unimplemented")
	def createUrl(self):
		# Returns the webservice URL
		return "module/%s/rest/reference_module/%s" % (self.getInternalModuleName(), self.deployer.module)
	def execute(self):
		# Executes the request and returns the DOM XML root node
		body = StringIO()
		
		url = self.deployer.options.baseurl
		if (not url.endswith("/")):
			url = url + "/"
		url = url + self.createUrl()
		
		c = pycurl.Curl()
		c.setopt(c.USERPWD, str("%s:%s" % (self.deployer.options.user, self.deployer.options.key)))
		c.setopt(c.URL, url)		
		c.setopt(c.WRITEFUNCTION, body.write)
		c.setopt(c.FOLLOWLOCATION, 1)
		
		print "> Requesting %s..." % url
		c.perform()
		
		if (c.getinfo(pycurl.HTTP_CODE) == 401):
			raise ResultException(str("HTTP status %s : authentication failed - user or key is not valid" % c.getinfo(pycurl.HTTP_CODE)))
		if (c.getinfo(pycurl.HTTP_CODE) != 200):
			raise ResultException(str("HTTP status %s" % c.getinfo(pycurl.HTTP_CODE)))
		
		c.close()
		contents = body.getvalue()
		
		xmldoc = minidom.parseString(contents)
		rest = xmldoc.getElementsByTagName('rest')[0]
		return rest
	
class EnvAction(Action):
	# Base class for an action depending on an environment
	def checkArgs(self):
		if (not self.deployer.options.env):
			raise ResultException("This action requires an environment")		
	def createUrl(self):		
		return Action.createUrl(self) + "/cle_environnement/%s" % self.deployer.options.env
	
class ApacheAction(EnvAction):
	def getInternalModuleName(self):
		return "apache"	
	def checkArgs(self):
		EnvAction.checkArgs(self)
		commands = ("status", "restart", "start", "stop")
		if (len(self.deployer.args) < 3):
			raise ResultException("This action requires a command as last parameter (%s)" % ", ".join(commands))
		command = self.deployer.args[2]
		if (not command in commands):
			raise ResultException("Invalid command (valid commands are : %s)" % ", ".join(commands))
		self.command = command
	def createUrl(self):
		return EnvAction.createUrl(self) + "/command/%s" % self.command

class TomcatAction(EnvAction):
	def getInternalModuleName(self):
		return "tomcat"
	def checkArgs(self):
		EnvAction.checkArgs(self)
		commands = ("status", "restart", "start", "stop", "force-stop")
		if (len(self.deployer.args) < 3):
			raise ResultException("This action requires a command as last parameter (%s)" % ", ".join(commands))
		command = self.deployer.args[2]
		if (not command in commands):
			raise ResultException("Invalid command (valid commands are : %s)" % ", ".join(commands))
		self.command = command
	def createUrl(self):
		return EnvAction.createUrl(self) + "/command/%s" % self.command
	
class ContextAction(EnvAction):
	def getInternalModuleName(self):
		return "contexte"
	def checkArgs(self):
		EnvAction.checkArgs(self)
		commands = ("view", "reload", "deploy", "undeploy", "redeploy")
		if (len(self.deployer.args) < 3):
			raise ResultException("This action requires a command as last parameter (%s)" % ", ".join(commands))
		command = self.deployer.args[2]
		if (not command in commands):
			raise ResultException("Invalid command (valid commands are : %s)" % ", ".join(commands))
		self.command = command
	def createUrl(self):
		return EnvAction.createUrl(self) + "/command/context-%s/log/%s" % (self.deployer.args[2], self.deployer.options.log)
	
class BatchAction(EnvAction):
	def getInternalModuleName(self):
		return "batch"
	def checkArgs(self):
		EnvAction.checkArgs(self)
		commands = ("status", "restart", "start", "stop", "force-stop")
		if (len(self.deployer.args) < 3):
			raise ResultException("This action requires a command as last parameter (%s)" % ", ".join(commands))
		command = self.deployer.args[2]
		if (not command in commands):
			raise ResultException("Invalid command (valid commands are : %s)" % ", ".join(commands))
		self.command = command
	def createUrl(self):
		return EnvAction.createUrl(self) + "/command/%s" % self.command
	
class DeliverAction(Action):
	def getInternalModuleName(self):
		return "installation_livraison_%s" % self.deployer.moduleType
	def checkArgs(self):
		Action.checkArgs(self)
		if (len(self.deployer.args) < 3):
			raise ResultException("This action requires a filename")
		self.filename = self.deployer.args[2]
		if not os.path.exists(self.filename):
			raise ResultException("File %s doesn't exist or you don't have access permissions." % self.filename)
	def execute(self):
		body = StringIO()
		
		c = pycurl.Curl()
		c.setopt(c.USERPWD, str("%s:%s" % (self.deployer.options.user, self.deployer.options.key)))
		c.setopt(c.URL, str("%s/%s" % (self.deployer.options.baseurl, self.createUrl())))
		c.setopt(c.WRITEFUNCTION, body.write)
		c.setopt(c.FOLLOWLOCATION, 1)

		fields = [("livrable"   , (c.FORM_FILE    , self.filename))]
		if self.deployer.options.comment != None:
			fields.append(("commentaire", self.deployer.options.comment))
		c.setopt(c.HTTPPOST, fields)

		c.perform()
		
		if (c.getinfo(pycurl.HTTP_CODE) != 200):
			raise ResultException(str("HTTP status %s" % c.getinfo(pycurl.HTTP_CODE)))
		
		c.close()
		contents = body.getvalue()
		
		xmldoc = minidom.parseString(contents)
		rest = xmldoc.getElementsByTagName('rest')[0]
		return rest
	
class InstallAction(EnvAction):
	def getInternalModuleName(self):
		return "installation_%s" % self.deployer.moduleType
	def checkArgs(self):
		EnvAction.checkArgs(self)
		if (len(self.deployer.args) < 3):
			raise ResultException("This action requires a version")
		self.version = self.deployer.args[2]
	def createUrl(self):
		return EnvAction.createUrl(self) + "/version/%s" % self.version

class ImportAction(Action):
	def checkArgs(self):
		Action.checkArgs(self)
		if (len(self.deployer.args) < 3):
			raise ResultException("This action requires a filename")
		self.filename = self.deployer.args[2]
		if not os.path.exists(self.filename):
			raise ResultException("File %s doesn't exist or you don't have access permissions." % self.filename)
	def createUrl(self):
		return "/admin/import/rest"
	def execute(self):
		body = StringIO()
		
		c = pycurl.Curl()
		c.setopt(c.USERPWD, str("%s:%s" % (self.deployer.options.user, self.deployer.options.key)))
		c.setopt(c.URL, str("%s/%s" % (self.deployer.options.baseurl, self.createUrl())))
		c.setopt(c.WRITEFUNCTION, body.write)
		c.setopt(c.FOLLOWLOCATION, 1)
		c.setopt(c.HTTPPOST, [("file", (c.FORM_FILE, self.filename))])		

		c.perform()
		
		if (c.getinfo(pycurl.HTTP_CODE) != 200):
			raise ResultException(str("HTTP status %s" % c.getinfo(pycurl.HTTP_CODE)))
		
		c.close()
		contents = body.getvalue()
		
		xmldoc = minidom.parseString(contents)
		rest = xmldoc.getElementsByTagName('rest')[0]
		return rest

class Deployer:
	def __init__(self, actions, options, args):
		self.actions = actions
		self.options = options
		self.args = args
		self.module = args[0]
		self.action = args[1]

	def run(self):
		pass

class ModuleDeployer(Deployer):
	# Used to launch a command on the server and follow its status
	def __init__(self, actions, options, args):
		Deployer.__init__(self, actions, options, args)
		try:
			self.moduleType = args[0].rsplit("-", 1)[1];			
		except:
			raise ResultException("The given module doesn't provide the module type.");
		if (not self.moduleType in ("batch", "cronbatch", "webapp")):
			raise ResultException("The module type %s is not supported." % self.moduleType);
		
	def executeCommand(self):
		try:
			action = self.actions[self.action](self)
		except KeyError, error:
			raise ResultException("Unknown action (valid actions are : %s)" % ", ".join(sorted(self.actions.keys())))
		rest = action.execute()
		statusValue = getText(rest.getElementsByTagName('status')[0])
		if (statusValue == 'OK'):
			batchId = getText(rest.getElementsByTagName('batch')[0])
			return batchId
		else:
			message = getText(rest.getElementsByTagName('message')[0])
			raise ResultException(message)

	def followCommand(self, batchId):
		# Call the webservice
		body = StringIO()
		
		c = pycurl.Curl()
		c.setopt(c.USERPWD, str("%s:%s" % (self.options.user, self.options.key)))
		c.setopt(c.URL, str("%s/%s" % (self.options.baseurl, "module/command/rest/reference_module/" + self.module  + "/id/" + batchId)))
		c.setopt(c.WRITEFUNCTION, body.write)
		c.setopt(c.FOLLOWLOCATION, 1)
		c.perform()
		
		if (c.getinfo(pycurl.HTTP_CODE) != 200):
			raise ResultException(str("HTTP status %s" % c.getinfo(pycurl.HTTP_CODE)))
		
		c.close()
		contents = body.getvalue()
		
		xmldoc = minidom.parseString(contents)
		rest = xmldoc.getElementsByTagName('rest')[0]
		
		# Manage the response
		statusValue = getText(rest.getElementsByTagName('status')[0])
		if (statusValue == 'OK'):
			command = rest.getElementsByTagName('command')[0]
			try:
				done = int(getText(command.getElementsByTagName('done')[0]))
			except:
				done = 0
			commandStatus = int(getText(command.getElementsByTagName('status')[0]))
			return CommandResult(done, commandStatus, rest)
		else:
			message = getText(rest.getElementsByTagName('message')[0])
			raise ResultException(message)
		
	def run(self):
		result = self.executeCommand()
		batchId = result
		print "Executing command...",
		startTime = time.time()
		result = self.followCommand(batchId)
		currentStep = 0
		while not result.isDone():
			sys.stdout.write(".")
			sys.stdout.flush()
			time.sleep(1)
			result = self.followCommand(batchId)
		print
		command = getNode(result.getXml(), 'command')
		steps = getNode(command, 'steps')
		for step in steps.childNodes:
			label = getText(getNode(step, 'label'))
			try:
				aborted = step.attributes['aborted']
			except:
				aborted = False
			if (aborted):
				label += " (not done)"
			try:
				checkpoint = getNode(step, 'checkPoint')
			except:
				checkpoint = None
			if (checkpoint):
				style = getNode(checkpoint, 'style')
				if (getText(style) == 'subcheckpoint'):
					print "- %s" % label
				else:
					print
					print "# %s" % label
					print
			else: 
				try:
					report = getText(getNode(step, 'report')).strip()
					print "* %s :\n%s" % (label, report)
				except:
					print "* %s" % label
		endTime = time.time()
		print "Duration : %d seconds" % (endTime - startTime)
		print "Execution report : %s" % result.report()
		sys.exit(result.getStatus())

class AdminDeployer(Deployer):
	# Used to launch a command on the server and follow its status
	def __init__(self, actions, options, args):
		Deployer.__init__(self, actions, options, args)
	def run(self):
		try:
			action = self.actions[self.action](self)
		except KeyError, error:
			raise ResultException("Unknown action (valid actions are : %s)" % ", ".join(sorted(self.actions.keys())))

		rest = action.execute()

		# Manage the response
		statusValue = getText(rest.getElementsByTagName('status')[0])
		if statusValue in ('OK', 'ERROR'):
			output = rest.getElementsByTagName("output")[0]
			for step in output.childNodes:
				stepStatus = getText(getNode(step, 'status'))
				stepMessage = getText(getNode(step, 'message'))
				print "[%s] %s" % (stepStatus, stepMessage)
			if statusValue == 'OK':
				sys.exit(0)
			else:
				sys.exit(1)
		else:
			message = getText(rest.getElementsByTagName('message')[0])
			raise ResultException(message)

def createOptionParser(actions):
	parser = OptionParser(
		usage="%prog [options] <module> <action> [args]\n"
		+ "\nNote : <module> is the name of your module (ie, mymodule-webapp), or the reserved keyword \"admin\" for some administration tasks.\n"
		+ "\nAvailable actions are :\n- "
		+ "\n- ".join(sorted(actions.keys()))
		+ "\n\nUse '%prog [options] <module> <action>' without any args to have more help on a specific action. ", version="%prog " + VERSION
	)
	parser.add_option("-u", "--user", dest="user", help="Authentication username")
	parser.add_option("-k", "--key", dest="key", help="Authentication key")
	parser.add_option("--baseurl", dest="baseurl", help="Deployment server base url (The default is http://deploy.ipp93.cvf/)", default="http://deploy.ipp93.cvf/")
	parser.add_option("-e", "--env", dest="env", help="The environment key where the action will be processed (ex: itg, prp, prod, ...)")
	parser.add_option("-t", "--type", dest="type", help="This option is deprecated and has no more effect.")
	parser.add_option("-c", "--comment", dest="comment", help="Provides the comment when delivering a new module.")
	parser.add_option("--log", type="choice", choices=("no","error","always"), default="no", dest="log", help="Enables servers logs extraction.")
	return parser	

def main():
	try:
		actions = {
			'apache': ApacheAction,
			'tomcat': TomcatAction,
			'context': ContextAction,
			'batch': BatchAction,
			'deliver': DeliverAction,
			'install': InstallAction,
		}
		parser = createOptionParser(actions)
		
		(options, args) = parser.parse_args()
		
		if len(args) == 0:
			parser.print_help()
			sys.exit(1)

		if args[0] == 'admin':
			# Recreate a specific parser
			actions = {
				'import': ImportAction,
			}
			parser = createOptionParser(actions)

		if len(args) == 1:
			parser.error("Incorrect number of arguments : no action is given.")


		if args[0] == 'admin':
			deployer = AdminDeployer(actions, options, args)
		else:
			deployer = ModuleDeployer(actions, options, args)

		deployer.run()
				
	except ResultException, result:
		parser.error(result.getMessage())
		sys.exit(1)
	
if __name__ == "__main__":
	main()
