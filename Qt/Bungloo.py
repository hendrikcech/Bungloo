#!/usr/bin/env python2

import os, sys, pickle, subprocess, shutil
from PyQt4 import QtCore, QtGui, QtWebKit, QtNetwork

RUNNING_LOCAL = os.path.basename(sys.argv[0]) == "Bungloo.py"
RUNNING_ON_WINDOWS = os.name == "nt"

if RUNNING_LOCAL or RUNNING_ON_WINDOWS:
    import Windows, Helper
else:
    from bungloo import Windows, Helper

class Bungloo:

	def __init__(self):

		sslConfig = QtNetwork.QSslConfiguration.defaultConfiguration()
		sslConfig.setProtocol(QtNetwork.QSsl.TlsV1)
		QtNetwork.QSslConfiguration.setDefaultConfiguration(sslConfig)

		self.app = QtGui.QApplication(sys.argv)
		self.new_message_windows = []
		self.controller = Controller(self)
		self.console = Console()

		self.preferences = Windows.Preferences(self)
		self.preferences.show()

		self.oauth_implementation = Windows.Oauth(self)

		if self.controller.stringForKey("user_access_token") != "":
			self.authentification_succeded()

		self.app.exec_()

	def resources_path(self):
   		if RUNNING_LOCAL:
			return os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), '..'))
		else:
			return Helper.Helper.get_resource_path()

	def resources_uri(self):
		return "file://localhost/" + os.path.abspath(os.path.join(self.resources_path(), "WebKit"))

	def login_with_entity(self, entity):
		self.controller.setStringForKey(entity, "entity")
		self.oauth_implementation.login()

	def authentification_succeded(self):
		self.preferences.hide()
		if hasattr(self, "oauth_implementation"):
			self.oauth_implementation.hide()
		self.preferences.active(False)
		self.init_web_views()

	def init_web_views(self):
		if not hasattr(self, "timeline"):
			self.timeline = Windows.Timeline(self)
		else:
			self.timeline.evaluateJavaScript("start('timeline')")
		self.timeline.show()
		self.find_entity = Windows.FindEntity(self)

	def find_entity_show(self):
		self.find_entity.show()

	def timeline_show(self):
		self.timeline.show()
		self.timeline.evaluateJavaScript("bungloo.sidebar.onTimeline();")

	def mentions_show(self):
		self.controller.unreadMentions(0)
		self.timeline.evaluateJavaScript("bungloo.sidebar.onMentions();")

	def conversation_show(self):
		self.timeline.evaluateJavaScript("bungloo.sidebar.onConversation();")
	
	def profile_show(self):
		self.timeline.evaluateJavaScript("bungloo.sidebar.onEntityProfile();")

	def search_show(self):
		self.timeline.evaluateJavaScript("bungloo.sidebar.onSearch();")

	def open_about(self):
		self.controller.openURL("http://jabs.nu/bungloo")

	def log_out(self):
		self.oauth_implementation.log_out()
		self.timeline.hide()
		self.preferences.show()
		self.timeline.evaluateJavaScript("bungloo.sidebar.logout()")


class Controller(QtCore.QObject):

	def __init__(self, app):
		QtCore.QObject.__init__(self)
		self.app = app

		oldpath = os.path.expanduser('~/.bungloo/')
		if os.path.isdir(oldpath):
			shutil.copytree(oldpath, os.path.expanduser('~/.config/bungloo/'))
			shutil.rmtree(os.path.expanduser('~/.bungloo/'))

		if not os.path.exists(os.path.expanduser("~/.config/bungloo/")):
			os.makedirs(os.path.expanduser("~/.config/bungloo/"))
		
		self.config_path = os.path.expanduser('~/.config/bungloo/bungloo.cfg')

		if os.access(self.config_path, os.R_OK):
			with open(self.config_path, 'r') as f:
				self.config = pickle.load(f)
		else:
			print self.config_path + " is not readable"
			self.config = {}

	@QtCore.pyqtSlot(str, str)
	def setStringForKey(self, string, key):
		string, key = str(string), str(key)
		self.config[key] = string
		try:
			with open(self.config_path, 'w+') as f:
				pickle.dump(self.config, f)
		except IOError as e:
			print self.config_path + " is not writable"
			print "I/O error({0}): {1}".format(e.errno, e.strerror)

	@QtCore.pyqtSlot(str, result=str)
	def stringForKey(self, key):
		key = str(key)
		if key in self.config:
			return self.config[key]
		else:
			return ""

	@QtCore.pyqtSlot(str)
	def openAuthorizationURL(self, url):
		self.app.oauth_implementation.handle_authentication(str(url))

	@QtCore.pyqtSlot(str)
	def openURL(self, url):
		QtGui.QDesktopServices.openUrl(QtCore.QUrl(url, QtCore.QUrl.TolerantMode))

	def openQURL(self, url):
		QtGui.QDesktopServices.openUrl(url)

	@QtCore.pyqtSlot()
	def loggedIn(self):
		self.app.authentification_succeded()

	@QtCore.pyqtSlot(int)
	def unreadMentions(self, count):
		script = "bungloo.sidebar.setUnreadMentions({});".format(int(count))
		self.app.timeline.evaluateJavaScript(script)

	@QtCore.pyqtSlot(str, str, str, str)
	def notificateUserAboutMentionFromNameWithPostIdAndEntity(self, text, name, post_id, entity):
		try:
			subprocess.check_output(['kdialog', '--passivepopup', name + ' mentioned you: ' + text])
		except OSError:
			try:
				subprocess.check_output(['notify-send', '-i', 'dialog-information', name + ' mentioned you on Tent', text])
			except OSError:
				pass

	@QtCore.pyqtSlot(str)
	def openNewMessageWidow(self, string):
		new_message_window = Windows.NewPost(self.app)
		new_message_window.show()
		new_message_window.setAttribute(QtCore.Qt.WA_DeleteOnClose)
		self.app.new_message_windows.append(new_message_window)

	@QtCore.pyqtSlot(str, str, str, bool)
	def openNewMessageWindowInReplyTostatusIdwithStringIsPrivate(self, entity, status_id, string, is_private):
		new_message_window = Windows.NewPost(self.app)
		new_message_window.inReplyToStatusIdWithString(entity, status_id, string)
		new_message_window.setIsPrivate(is_private)
		new_message_window.show()
		new_message_window.setAttribute(QtCore.Qt.WA_DeleteOnClose)
		self.app.new_message_windows.append(new_message_window)

	def sendMessage(self, message):
		text = message.text
		text = unicode.replace(text, "\\", "\\\\")
		text = unicode.replace(text, "\"", "\\\"")
		text = unicode.replace(text, "\n", "\\n")

		in_reply_to_status_id = ""
		if message.inReplyTostatusId is not None:
			in_reply_to_status_id = message.inReplyTostatusId

		in_reply_to_entity = ""
		if message.inReplyToEntity is not None:
			in_reply_to_entity = message.inReplyToEntity

		locationObject = "null"
		#if (post.location) {
		#    locationObject = [NSString stringWithFormat:@"[%f, %f]", post.location.coordinate.latitude, post.location.coordinate.longitude];
		#}

		imageFilePath = "null"
		if message.imageFilePath is not None:
			mimeType = subprocess.check_output(['file', '-b', '--mime', message.imageFilePath]).split(";")[0]
			base64 = open(message.imageFilePath, "rb").read().encode("base64").replace("\n", "")
			imageFilePath = "\"data:{};base64,{}\"".format(mimeType, base64)

		isPrivate = "false";
		if message.isPrivate:
			isPrivate = "true"

		func = u"bungloo.timeline.sendNewMessage(\"{}\", \"{}\", \"{}\", {}, {}, {});".format(text, in_reply_to_status_id, in_reply_to_entity, locationObject, imageFilePath, isPrivate)
		self.app.timeline.evaluateJavaScript(func)

	@QtCore.pyqtSlot(str, str)
	def showConversationForPostIdandEntity(self, postId, entity):
		func = "bungloo.sidebar.onConversation(); bungloo.conversation.showStatus('{}', '{}');".format(postId, entity)
		self.app.timeline.evaluateJavaScript(func)
		self.app.timeline.show()

	@QtCore.pyqtSlot(str)
	def showProfileForEntity(self, entity):
		func = "bungloo.sidebar.onEntityProfile(); bungloo.entityProfile.showProfileForEntity('{}');".format(entity)
		self.app.timeline.evaluateJavaScript(func)

	@QtCore.pyqtSlot(str, str)
	def notificateViewsAboutDeletedPostWithIdbyEntity(self, post_id, entity):
		f = ".postDeleted('{}', '{}')".format(post_id, entity);
		func = "bungloo.timeline" + f + ";"
		func += "bungloo.mentions" + f + ";"
		func += "bungloo.conversation" + f + ";"
		func += "bungloo.entityProfile" + f + ";"

		self.app.timeline.evaluateJavaScript(func)

	@QtCore.pyqtSlot(str)
	def authentificationDidNotSucceed(self, errorMessage):
		msgBox = QtGui.QMessageBox()
		msgBox.setText(errorMessage)
		msgBox.exec_()

	@QtCore.pyqtSlot(str, str)
	def alertTitleWithMessage(self, title, message):
		msgBox = QtGui.QMessageBox()
		msgBox.setText(title)
		msgBox.setInformativeText(message)
		msgBox.exec_()

	def logout(self, sender):
		print "logout is not implemented yet"


class Console(QtCore.QObject):

	@QtCore.pyqtSlot(str)
	def log(self, string):
		print "<js>: " + unicode(string)

	@QtCore.pyqtSlot(str)
	def error(self, string):
		print "<js ERROR>: " + unicode(string)

	@QtCore.pyqtSlot(str)
	def warn(self, string):
		print "<js WARN>: " + unicode(string)

	@QtCore.pyqtSlot(str)
	def notice(self, string):
		print "<js NOTICE>: " + unicode(string)

	@QtCore.pyqtSlot(str)
	def debug(self, string):
		print "<js DEBUG>: " + unicode(string)


if __name__ == "__main__":
	Bungloo()
