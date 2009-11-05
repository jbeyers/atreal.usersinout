import csv
from StringIO import StringIO

from zope.interface import implements

from Products.Five.browser import BrowserView
from Products.CMFCore.utils import getToolByName
from Products.statusmessages.interfaces import IStatusMessage

from atreal.usersinout import UsersInOutMessageFactory as _
from atreal.usersinout.config import CSV_HEADER, MEMBER_PROPERTIES

class UsersInOut (BrowserView):
    """ Users import and export as CSV files
    
    """
    
    def __call__(self):
        method = self.request.get('REQUEST_METHOD', 'GET')
        if (method != 'POST') or not int(self.request.form.get('form.submitted', 0)):
            return self.index()
        
        if self.request.form.get('form.button.Cancel'):
            return self.request.response.redirect('%s/plone_control_panel' \
                                                  % self.context.absolute_url())
            
        if self.request.form.get('form.button.Import'):
            return self.importUsers()

        if self.request.form.get('form.button.CSVErrors'):
            return self.getCSVWithErrors()
            
        if self.request.form.get('form.button.Export'):
            return self.exportUsers()            
    
    def getCSVTemplate(self):
        """ Return a CSV template to use when importing members """
        datafile = self._createCSV([])
        return self._createRequest(datafile.getvalue(), "users_sheet_template.csv")
    

    def importUsers(self):
        """ Import users from CSV file.
            In case of error, return a CSV file filled with the lines where
            errors occured.
            
        """
        file_upload = self.request.form.get('csv_upload', None)
        if file_upload is None or not file_upload.filename:
            return
        
        reader = csv.reader(file_upload)
        header = reader.next()
        
        if header != CSV_HEADER:
            msg = _('Wrong specification of the CSV file. Please correct it and retry.')
            type = 'error'
            IStatusMessage(self.request).addStatusMessage(msg, type=type)
            return
        
        pr = getToolByName(self.context, 'portal_registration')
        invalidLines = []
        i = 0
        for line in reader:
            datas = dict(zip(header, line))
            try:
                groups = datas.pop('groups').split(',')
                username = datas['username']
                password = datas.pop('password')
                roles = datas.pop('roles').split(',')
                pr.addMember(username, password, roles, [], datas)
                i += 1
            except:
                invalidLines.append(line)
                print "Invalid line : %s" % username
        
        if invalidLines:
            datafile = self._createCSV(invalidLines)
            self.request['csverrors'] = True
            self.request.form['users_sheet_errors'] = datafile.getvalue()
            msg = _('Some errors occured. Please check your CSV syntax and retry.')
            type = 'error' 
        else:
            msg, type = _('Members successfully imported.'), 'info'

        IStatusMessage(self.request).addStatusMessage(msg, type=type)
        self.request['results'] = i
        return self.index()


    def getCSVWithErrors(self):
        """ Return a CSV file that contains lines witch failed """
        
        users_sheet_errors = self.request.form.get('users_sheet_errors', None)
        if users_sheet_errors is None:
            return # XXX
        
        return self._createRequest(users_sheet_errors, "users_sheet_errors.csv")


    def exportUsers(self):
        """ Export users within CSV file.
            
        """
        self.pms = getToolByName(self.context,'portal_membership')
        datafile = self._createCSV(self._getUsersInfos())
        return self._createRequest(datafile.getvalue(), "users_sheet_export.csv")


    def _getUsersInfos(self):
        """ Generator filled with the members data """
        acl = getToolByName(self.context, 'acl_users')
        for user in acl.searchUsers():
            yield self._getUserData(user['userid'])
    
    
    def _getUserData(self,userId):
        member = self.pms.getMemberById(userId)
        props = [userId, '', ''] # userid, password, roles - XXX to implement
        for p in MEMBER_PROPERTIES:
            props.append(member.getProperty(p))
        props.append('') # groups - XXX to implement
        return props


    def _createCSV(self, lines):
        """ Write header + lines within the CSV file """
        datafile = StringIO()
        writor = csv.writer(datafile)
        writor.writerow(CSV_HEADER)
        map(writor.writerow, lines)
        return datafile


    def _createRequest(self, data, filename):
        """ Create the request to be returned. Add the right header and the
            CSV file.
            
        """
        self.request.response.addHeader('Content-Disposition', "attachment; filename=%s" % filename)
        self.request.response.addHeader('Content-Type', "text/csv")
        self.request.response.addHeader('Content-Length', "%d" % len(data))
        self.request.response.addHeader('Pragma', "no-cache")
        self.request.response.addHeader('Cache-Control', "must-revalidate, post-check=0, pre-check=0, public")
        self.request.response.addHeader('Expires', "0")
        return data
    