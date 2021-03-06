from __future__ import with_statement

import sys, os
import mongogut
import traceback
from flask import (Blueprint, request, url_for, Response, current_app as app, abort, render_template, jsonify)
from flask import  session, g, redirect, flash, escape, make_response
import flask
import simplejson as json
from random import choice
from mongogut.utilities import gettype
from flask.ext.mongoengine import MongoEngine
from flask.ext.mongoengine.wtf import model_form
from flask_debugtoolbar import DebugToolbarExtension
from flask.ext.login import current_user
from mongogut import ptassets as itemsandtags
from mongogut.errors import doabort, MongoGutError
import datetime
from werkzeug import Response
from mongoengine import Document
from bson.objectid import ObjectId


POTENTIALUSERSTRING="""
<p>
The SAO/NASA Astrophysics Data System (ADS) is a Digital Library portal for researchers in Astronomy and
Physics, operated by the Smithsonian Astrophysical Observatory (SAO) under a NASA grant. The ADS maintains
three bibliographic databases containing more than 10.8 million records: Astronomy and Astrophysics, Physics,
and arXiv e-prints. The main body of data in the ADS consists of bibliographic records, which are searchable
through highly customizable query forms, and full-text scans of much of the astronomical literature which
can be browsed or searched via our full-text search interface at <a href="http://labs.adsabs.harvard.edu/adsabs/">http://labs.adsabs.harvard.edu/adsabs/</a>."
</p>
"""

POTENTIALUSERSTRING2="""
<p>
If you already have an account at ADS, you can go to <a href="http://labs.adsabs.harvard.edu/adsabs/user/">http://labs.adsabs.harvard.edu/adsabs/user/</a>, sign in, and click the %s link there to accept.
</p>
<p>
If you do not already have an ADS account, please <a href="http://labs.adsabs.harvard.edu/adsabs/user/signup">Sign up</a>! You will then be able to accept the invite from your account's Groups page.
</p>
"""

adsgut_blueprint = Blueprint('adsgut', __name__,
                            template_folder="templates",
                            static_folder='static',
                            url_prefix='/adsgut',

)

adsgut_app=app
adsgut=adsgut_blueprint
from adsabs.extensions import mongoengine
from adsabs.extensions import solr

#tech to allow creating json from MomgoEngine Objects
def todfo(ci):
    cijson=ci.to_json()
    cidict=json.loads(cijson)
    return cidict

def todfl(cil):
    cijsonl=[e.to_json() for e in cil]
    cidictl=[json.loads(e) for e in cijsonl]
    return cidictl


class MongoEngineJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Document):
            return obj.to_mongo()
        elif isinstance(obj, ObjectId):
            return unicode(obj)
        elif isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        try:
            iterable = iter(obj)
        except TypeError:
            pass
        else:
            return list(iterable)
        return json.JSONEncoder.default(self, obj)

def jsonify(*args, **kwargs):
    """ jsonify with support for MongoDB ObjectId
    """
    return Response(json.dumps(dict(*args, **kwargs), cls=MongoEngineJsonEncoder), mimetype='application/json')



#This next set of functions is used to obtain various quantities
#from http request GET and POST dictionaries in flask.

#FOR GET
def _dictg(k,d, listmode=False):
    val=d.get(k, [None])
    if d.has_key(k):
        d.pop(k)
    if listmode:
        return val
    else:
        return val[0]

#FOR POST
def _dictp(k,d, default=None):
    val=d.get(k, default)
    if d.has_key(k):
        d.pop(k)
    return val

#gets a user from key useras in a POST request
def _userpostget(g, postdict):
    nick=_dictp('useras', postdict)
    if nick:
        useras=g.db._getUserForNick(g.currentuser, nick)
    else:
        useras=g.currentuser
    return useras

#gets a user from key useras in a GET request
#userthere is used incase you want items just pertinent to the user
def _userget(g, qdict):
    nick=_dictg('useras', qdict)
    userthere=_dictg('userthere', qdict)
    if nick:
        useras=g.db._getUserForNick(g.currentuser, nick)
    else:
        useras=g.currentuser
    if userthere:
        usernick=useras.nick
    else:
        usernick=False
    return useras, usernick

#gets a sortspec. This looks like posting__whenposted:True
#which corresponds to and ascending sort. notee that i am currently
#exposing the inners of the database. it would be better to use a table
#to map this to user friendly names. TODO.
def _sortget(qdict):
    #a serialixed dict of ascending and field
    sortstring=_dictg('sort', qdict)
    if not sortstring:
        return {'field':'posting__whenposted', 'ascending':False}
    sort={}
    sort['field'], sort['ascending'] = sortstring.split(':')
    sort['ascending']=(sort['ascending']=='True')
    return sort

#sortspec from POST
def _sortpostget(qdict):
    #a serialixed dict of ascending and field
    sortstring=_dictp('sort', qdict)
    if not sortstring:
        return {'field':'posting__whenposted', 'ascending':False}
    sort={}
    sort['field'], sort['ascending'] = sortstring.split(':')
    sort['ascending']=(sort['ascending']=='True')
    return sort

#criteria is a multiple ampersand list, with colon separators.
#eg criteria=basic__fqin:eq:something&criteria=
#we create from it a criteria list of dicts
def _criteriaget(qdict):
    critlist=_dictg('criteria', qdict, True)
    if not critlist[0]:
        return False
    crit=[]
    for ele in critlist:
        cr={}
        cr['field'], cr['op'], cr['value'] = ele.split(':',2)
        crit.append(cr)
    return crit

#a serialised dict of arbitrary keys, with mongo style encoding
#operators are not represented here.(equality is assumed)
def _queryget(qdict):
    querylist=_dictg('query', qdict, True)
    if not querylist[0]:
        return {}
    q={}
    for ele in querylist:
        field, value = ele.split(':',1)
        if not q.has_key(field):
            q[field]=[]
        q[field].append(value)
    return q

#this is for pagination in the form pagetuplle=15:30
#the first is the item number to start from(offset), the second is the pagestyle.
def _pagtupleget(qdict):
    pagtuplestring=_dictg('pagtuple', qdict)
    if not pagtuplestring:
        return None
    plist=pagtuplestring.split(':')
    pagtuple=[int(e) if e else -1 for e in pagtuplestring.split(':')]
    return pagtuple

#gets a list of items using their fqins
def _itemsget(qdict):
    itemlist=_dictg('items', qdict, True)
    if not itemlist[0]:
        return []
    return itemlist

#like above, but uses post
def _itemspostget(qdict):
    itemlist=_dictp('items', qdict)
    if not itemlist:
        return []
    return itemlist

#gets bibcodes from POST
def _bibcodespostget(qdict):
    itemlist=_dictp('bibcode', qdict)
    if not itemlist:
        return []
    return itemlist

#gets a list of libraries (using their fqpns)
def _postablesget(qdict):
    plist=_dictp('postables', qdict)
    if not plist:
        return []
    return plist

#get items and tags from the POST
#format is BLA
def _itemstagspostget(qdict):
    itemstagslist=_dictp('itemsandtags', qdict)
    if not itemstagslist:
        return []
    return itemstagslist


#get tag specs from the POST
#format is BLA
def _tagspecspostget(qdict):
    tagspecs=_dictp('tagspecs', qdict)
    if not tagspecs:
        return {}
    return tagspecs



import uuid

#a before_request is flask's place of letting you run code before 
#the request is carried out. here is where we get info about the user
#from the database and all that

#current_user is obtained from the flask session
@adsgut.before_request
def before_request():
    try:
        #get the adsid which should be the email of the user
        adsid=current_user.get_username()
        #try getting the cookie id as well
        cookieid=current_user.get_id()
    except:
        #this fails if the user is not logged in. then set adsid to python None
        adsid=None
    #set up the database, and attach the database to the global g object.
    p=itemsandtags.Postdb(mongoengine)
    w=p.whosdb
    g.db=w
    g.dbp=p
    if not adsid:
        #if user not logged in, set user to the 'anonymouse' user
        adsid='anonymouse'
        user=g.db._getUserForAdsid(None, adsid)
    else:
        try:#look up the user based on their cookieid
            user=g.db._getUserForCookieid(None, cookieid)
            if user.adsid != adsid:#user changed their email
                user.adsid = adsid
                user.save(safe=True)
        except:
            #if we couldnt look up the user based on their cookieid
            #this situation can happen when a user is invited, has logged in
            #on classic or main, but is not in our adsgut system as yet
            adsgutuser=g.db._getUserForNick(None, 'adsgut')
            adsuser=g.db._getUserForNick(adsgutuser, 'ads')
            #we dont have the cookie, but we might have the adsid, because he was invited earlier
            try:#partially in our database
              user=g.db._getUserForAdsid(None, adsid)
              #take whatever cookieid the ads server allocated, and save it
              user.cookieid=cookieid
              user.save(safe=True)
            except:#not at all in our database
              #TODO: IF the next two dont happen transactionally we run into issues. Later we make this transactional
              #if the user was not invited, and not already there in adsgut database
              #this will happen the first time a user clicks libraries in the
              #profile page
              user=g.db.addUser(adsgutuser,{'adsid':adsid, 'cookieid':cookieid})
            #add the user to the flagship ads app, at the very least, to complete user
            #being in our database(addUser does not do this, bcoz the user
            #may partially exist in our database thanks to invitation)
            user, adspubapp = g.db.addUserToMembable(adsuser, 'ads/app:publications', user.nick)

    g.currentuser=user

#######################################################################################################################
#Information about users, groups, and apps
#######################################################################################################################



#this url gets information about a user
import simplejson as json
@adsgut.route('/user/<nick>')
def userInfo(nick):
    user=g.db.getUserInfo(g.currentuser, nick)
    #get additional info about user's libraries, including the reason
    #why the user is in the library
    postablesother, names = user.membableslibrary(pathinclude_p=True)
    #crikey stupid hack to have to do this bcoz of jsonify introspecting
    #mongoengine objects only
    jsons = [e.to_json() for e in postablesother]
    ds=[]
    for i, j in enumerate(jsons):
        d = json.loads(j)
        if names[d['fqpn']][0][2]==d['fqpn']:#direct membership overrides all else
            d['reason'] = ''
        else:
            reasons=[e[1] for e in names[d['fqpn']]]
            #eliminate all libraries (many!) the user is in because
            #os being part of the public group
            #(TODO: might be better done cleaner in membableslibrary)
            elim=[]
            for j,r in enumerate(reasons):
                if r=='group:public' and len(reasons) > 1:
                    elim.append(j)
            for j in elim:
                del reasons[j]
            #print "R2", reasons
            d['reason'] = ",".join(reasons)
        ds.append(d)
    #return information about the user and their libraries
    ujson = jsonify(user=user, postablelibs=ds)
    return ujson

from flask.ext.wtf import Form, RecaptchaField
from wtforms import TextField, BooleanField, HiddenField
from wtforms.validators import DataRequired, Email

class InviteForm(Form):
    memberable = TextField('username', validators=[DataRequired(), Email()])
    op = HiddenField(default="invite")
    changerw = BooleanField("Can Post?")
    recaptcha = RecaptchaField()

class InviteFormGroup(Form):
    memberable = TextField('username', validators=[DataRequired(), Email()])
    op = HiddenField(default="invite")
    recaptcha = RecaptchaField()

#The next two URL's get the user profile in terms of all the libraries the user is
#in. See https://dl.dropboxusercontent.com/u/75194/userprofile.png
@adsgut.route('/user/<nick>/profile/html')
def userProfileHtml(nick):
    user=g.db.getUserInfo(g.currentuser, nick)
    return render_template('userprofile.html', theuser=user, useras=g.currentuser)

@adsgut.route('/email/<adsid>/profile/html')
def userProfileFromAdsidHtml(adsid):
    user=g.db.getUserInfoFromAdsid(g.currentuser, adsid)
    return render_template('userprofile.html', theuser=user, useras=g.currentuser)

#Thes next two creates a profile for the groups the user has.
#see https://dl.dropboxusercontent.com/u/75194/usergroupprofile.png
@adsgut.route('/user/<nick>/profilegroups/html')
def userProfileGroupsHtml(nick):
    user=g.db.getUserInfo(g.currentuser, nick)
    return render_template('userprofilegroups.html', theuser=user, useras=g.currentuser)

@adsgut.route('/email/<adsid>/profilegroups/html')
def userProfileGroupsFromAdsidHtml(adsid):
    user=g.db.getUserInfoFromAdsid(g.currentuser, adsid)
    return render_template('userprofilegroups.html', theuser=user, useras=g.currentuser)

#the libraries, apps and groups a user is directly in
#it should be called membablesuserisin but we are going with the historical url
@adsgut.route('/user/<nick>/postablesuserisin')
def postablesUserIsIn(nick):
    useras=g.db.getUserInfo(g.currentuser, nick)
    allpostables=g.db.membablesForUser(g.currentuser, useras)
    groups=[e['fqpn'] for e in allpostables if e['ptype']=='group']
    libraries=[e['fqpn'] for e in allpostables if e['ptype']=='library']
    apps=[e['fqpn'] for e in allpostables if e['ptype']=='app']
    groups.remove("adsgut/group:public")
    libraries.remove("adsgut/library:public")
    libraries.remove(useras.nick+"/library:default")
    return jsonify(groups=groups, libraries=libraries, apps=apps)

#this gets the libraries the user can access (write to is a not entirely
#accurate term because we do include read-only libraries here). the critical
#thing is that this includes libraires we are in due to membership in a group.
@adsgut.route('/user/<nick>/postablesusercanwriteto')
def postablesUserCanWriteTo(nick):
    useras=g.db.getUserInfo(g.currentuser, nick)
    allpostables=g.db.membablesUserCanWriteTo(g.currentuser, useras)
    #groups=[e['fqpn'] for e in allpostables if e['ptype']=='group']
    libraries=[e['fqpn'] for e in allpostables if e['ptype']=='library']
    #apps=[e['fqpn'] for e in allpostables if e['ptype']=='app']
    #print "GLA", groups, libraries, apps
    #groups.remove("adsgut/group:public")
    libraries.remove("adsgut/library:public")
    libraries.remove(useras.nick+"/library:default")
    return jsonify(groups=[], libraries=libraries, apps=[])

#groups user is in, minus the public grouo
@adsgut.route('/user/<nick>/groupsuserisin')
def groupsUserIsIn(nick):
    useras=g.db.getUserInfo(g.currentuser, nick)
    groups=[e['fqpn'] for e in g.db.membablesForUser(g.currentuser, useras, "group")]
    groups.remove("adsgut/group:public")
    return jsonify(groups=groups)

# groups user owns
@adsgut.route('/user/<nick>/groupsuserowns')
def groupsUserOwns(nick):
    useras=g.db.getUserInfo(g.currentuser, nick)
    groups=[e['fqpn'] for e in g.db.ownerOfMembables(g.currentuser, useras, "group")]
    return jsonify(groups=groups)

# groups user is invited to
@adsgut.route('/user/<nick>/groupsuserisinvitedto')
def groupsUserIsInvitedTo(nick):
    useras=g.db.getUserInfo(g.currentuser, nick)
    groups=[e['fqpn'] for e in g.db.membableInvitesForUser(g.currentuser, useras, "group")]
    return jsonify(groups=groups)

# apps user is in
@adsgut.route('/user/<nick>/appsuserisin')
def appsUserIsIn(nick):
    useras=g.db.getUserInfo(g.currentuser, nick)
    apps=[e['fqpn'] for e in g.db.membablesForUser(g.currentuser, useras, "app")]
    return jsonify(apps=apps)


#apps user owns. not used yet
@adsgut.route('/user/<nick>/appsuserowns')
def appsUserOwns(nick):
    useras=g.db.getUserInfo(g.currentuser, nick)
    apps=[e['fqpn'] for e in g.db.ownerOfMembables(g.currentuser, useras, "app")]
    return jsonify(apps=apps)

#apps user is invited to: not used yet.
@adsgut.route('/user/<nick>/appsuserisinvitedto')
def appsUserIsInvitedTo(nick):
    useras=g.db.getUserInfo(g.currentuser, nick)
    apps=[e['fqpn'] for e in g.db.membableInvitesForUser(g.currentuser, useras, "app")]
    return jsonify(apps=apps)


#libraries user is in directly
@adsgut.route('/user/<nick>/librariesuserisin')
def librariesUserIsIn(nick):
    useras=g.db.getUserInfo(g.currentuser, nick)
    libs=[e['fqpn'] for e in g.db.membablesUserCanAccess(g.currentuser, useras, "library")]
    return jsonify(libraries=libs)

#all the libraries the user is in
@adsgut.route('/user/<nick>/librariesusercanwriteto')
def librariesUserCanWriteTo(nick):
    useras=g.db.getUserInfo(g.currentuser, nick)
    libs=[e['fqpn'] for e in g.db.membablesUserCanWriteTo(g.currentuser, useras, "library")]
    return jsonify(libraries=libs)

#the libraries a user owns
@adsgut.route('/user/<nick>/librariesuserowns')
def librariesUserOwns(nick):
    useras=g.db.getUserInfo(g.currentuser, nick)
    libs=[e['fqpn'] for e in g.db.ownerOfMembables(g.currentuser, useras, "library")]
    return jsonify(libraries=libs)

#libraries a user is invited to
@adsgut.route('/user/<nick>/librariesuserisinvitedto')
def librariesUserIsInvitedTo(nick):
    useras=g.db.getUserInfo(g.currentuser, nick)
    libs=[e['fqpn'] for e in g.db.membableInvitesForUser(g.currentuser, useras, "library")]
    return jsonify(libraries=libs)

#all the items saved in user's default library, currently not used
@adsgut.route('/user/<nick>/items')
def userItems(nick):
    useras=g.db.getUserInfo(g.currentuser, nick)
    num, vals=g.dbp.getItemsForQuery(g.currentuser, useras,
       {'library':[useras.nick+"/library:default"]} )
    #userdict={'count':num, 'items':[json.loads(v.to_json()) for v in vals]}
    return jsonify(count=num, items=vals)

#######################################################################################################################
#functions for creating groups and apps
#and for accepting invites.

#METHODS using POST have POST parameters on the right of the function
#######################################################################################################################

#create a group, app, or library, od type ptstr
def createMembable(g, request, ptstr):
    spec={}
    jsonpost=dict(request.json)
    #get user and name from POST json
    useras=_userpostget(g,jsonpost)
    name=_dictp('name', jsonpost)
    if not name:
        doabort("BAD_REQ", "No Name Specified")
    #get description from POST
    description=_dictp('description', jsonpost, '')
    spec['creator']=useras.basic.fqin
    spec['name']=name
    spec['description']=description
    postable=g.db.addMembable(g.currentuser, useras, ptstr, spec)
    return postable

#create group/app/library. In our code we tend to use
#createMembable directly, rather than these endpoints.
#the useras is optional, vurrentuser is used otherwise

@adsgut.route('/group', methods=['POST'])#groupname/[description]/[useras]
def createGroup():
    if request.method == 'POST':
        newgroup=createMembable(g, request, "group")
        return jsonify(postable=newgroup)
    else:
        doabort("BAD_REQ", "GET not supported")

@adsgut.route('/app', methods=['POST'])#name/[description]/[useras]
def createApp():
    if request.method == 'POST':
        newapp=createMembable(g, request, "app")
        return jsonify(postable=newapp)
    else:
        doabort("BAD_REQ", "GET not supported")

@adsgut.route('/library', methods=['POST'])#name/[description]/[useras]
def createLibrary():
    if request.method == 'POST':
        newlibrary=createMembable(g, request, "library")
        return jsonify(postable=newlibrary)
    else:
        doabort("BAD_REQ", "GET not supported")

from adsabs.modules.user.user import AdsUser
from adsabs.modules.user.user import send_email_to_user

#creating an invitation to a group or library (or app: not implemented yet, TODO)
#this is a very different endpoint, only used from the per library or per group
#web pages to make invitations. it is NOT part of the API.
@adsgut.route('/postable/<po>/<pt>:<pn>/makeinvitations', methods=['POST'])
def makeInvitations(po, pt, pn):
    fqpn=po+"/"+pt+":"+pn
    if request.method == 'POST':
        if pt=="library":
            form = InviteForm()
        else:
            form = InviteFormGroup()
        if form.validate():
            #email of user being invited
            memberable=form.memberable.data
            changerw=False
            #for libraries, whether the read-write checkbox was checked
            if pt=="library":
              changerw=form.changerw.data
            if not memberable:
                 doabort("BAD_REQ", "No User Specified")
            #print "memberable", memberable, changerw
            potentialuserstring=""
            try:
                user=g.db._getUserForAdsid(g.currentuser, memberable)
            except:
                adsuser = AdsUser.from_email(memberable)
                #get the system users so that we can create a partial user
                adsgutuser=g.db._getUserForNick(None, 'adsgut')
                adsappuser=g.db._getUserForNick(adsgutuser, 'ads')
                if adsuser==None:#not in giovanni db, just add to ours
                    #add a potential user with 'NOCOOKIEYET'to our db
                    potentialuser=g.db.addUser(adsgutuser,{'adsid':memberable, 'cookieid':'NOCOOKIEYET-'+str(uuid.uuid4())})
                    user=potentialuser
                    potentialuserstring=POTENTIALUSERSTRING
                else:#already in giovanni db, add to ours
                    cookieid = adsuser.get_id()#get from giovanni db
                    adsid = adsuser.get_username()
                    user=g.db.addUser(adsgutuser,{'adsid':adsid, 'cookieid':cookieid})
                    #sice already there add to publications.
                    user, adspubapp = g.db.addUserToMembable(adsappuser, 'ads/app:publications', user.nick)
                    potentialuserstring=""
            potentialuserstring2=POTENTIALUSERSTRING2
            #ok got user, now invite by adding invitation into the database
            utba, p=g.db.inviteUserToMembable(g.currentuser, g.currentuser, fqpn, user, changerw)
            #queue up an invitation email
            emailtitle="Invitation to ADS Library %s" % pn
            ptmap={'group':'Group (and associated library)', 'library':"Library"}
            ptmap2={'group':'My Groups', 'library':"Libraries"}
            emailtext="%s has invited you to ADS %s %s." % (g.currentuser.adsid, ptmap[pt], pn)
            emailtext = emailtext+potentialuserstring+potentialuserstring2%ptmap2[pt]
            send_email_to_user(emailtitle, emailtext,[user.adsid])
            passdict={}
            passdict[pt+'owner']=po
            passdict[pt+'name']=pn
            flash("Invite sent", 'success')
            #redirect to user or group profile
            return redirect(url_for("adsgut."+pt+"ProfileHtml", **passdict))
        else:
            junk=1
        return profileHtmlNotRouted(po, pn, pt, inviteform=form)


#a very omnibus url allows making changes to postables, such as inviting
#(which we dont use because we use above for recaptcha purposes)
#but we use this one to accept invitations, change read-write, change descriptions
#you can also change ownership of a library/group, vut there is no UI for this
#anywhere in the system currently


#do NOT use invite, unless the user(and users email) is already in the system. This api function is NOT
#for random emails, otherwise a spammer might abuse it.

@adsgut.route('/postable/<po>/<pt>:<pn>/changes', methods=['POST'])#memberable/op/[description]
def doPostableChanges(po, pt, pn):
    #add permit to match user with groupowner
    fqpn=po+"/"+pt+":"+pn
    if request.method == 'POST':
        jsonpost=dict(request.json)
        memberable=_dictp('memberable', jsonpost)
        changerw=_dictp('changerw', jsonpost)
        if changerw==None:
            changerw=False
        #for inviting this is adsid(email) of user invited.
        #for accepting this is your own email(adsid)
        if not memberable:
            doabort("BAD_REQ", "No User Specified")
        op=_dictp('op', jsonpost)
        if not op:
            doabort("BAD_REQ", "No Op Specified")
        if op=="invite":
            try:
                memberable=g.db._getUserForAdsid(g.currentuser, memberable)
            except:
                adsuser = AdsUser.from_email(memberable)
                if adsuser==None:
                    doabort("BAD_REQ", "No such User")
                cookieid = adsuser.get_id()
                adsid = adsuser.get_username()
                adsgutuser=g.db._getUserForNick(None, 'adsgut')
                adsuser=g.db._getUserForNick(adsgutuser, 'ads')
                memberable=g.db.addUser(adsgutuser,{'adsid':adsid, 'cookieid':cookieid})
                #per usual add to publications
                memberable, adspubapp = g.db.addUserToMembable(adsuser, 'ads/app:publications', memberable.nick)

            utba, p=g.db.inviteUserToMembable(g.currentuser, g.currentuser, fqpn, memberable, changerw)
            emailtitle="Invitation to ADS Library %s" % pn
            emailtext="%s has invited you to ADS Library %s. Go to your libraries page to accept." % (g.currentuser.adsid, pn)
            send_email_to_user(emailtitle, emailtext,[memberable.adsid])

            return jsonify({'status':'OK', 'info': {'invited':utba.nick, 'to':fqpn}})
        elif op=='accept':
            memberable=g.db._getUserForAdsid(g.currentuser, memberable)
            me, p=g.db.acceptInviteToMembable(g.currentuser, fqpn, memberable)
            return jsonify({'status':'OK', 'info': {'invited':me.nick, 'to': fqpn, 'accepted':True}})
        elif op=='decline':
            memberable=g.db._getUserForAdsid(g.currentuser, memberable)
            #TODO: not implemented yet add something to invitations to mark declines.
            return jsonify({'status': 'OK', 'info': {'invited':memberable, 'to': fqpn, 'accepted':False}})
        elif op=='changeowner':
            #you must be the current owner
            memberable=g.db._getUserForAdsid(g.currentuser, memberable)
            newo, p=g.db.changeOwnershipOfMembable(g.currentuser, g.currentuser, fqpn, memberable)
            return jsonify({'status': 'OK', 'info': {'changedto':memberable, 'for': fqpn}})
        elif op=='togglerw':
            #here memberable could be a user or a group (whose membership to library you are toggling)
            #in either case here we need the fqin
            mtype=gettype(memberable)
            memberable=g.db._getMemberableForFqin(g.currentuser, mtype, memberable)
            mem, p = g.db.toggleRWForMembership(g.currentuser, g.currentuser, fqpn, memberable)
            return jsonify({'status': 'OK', 'info': {'user':memberable, 'for': fqpn}})
        elif op=='description':
            description=_dictp('description', jsonpost,'')
            mem, p = g.db.changeDescriptionOfMembable(g.currentuser, g.currentuser, fqpn, description)
            return jsonify({'status': 'OK', 'info': {'user':memberable, 'for': fqpn}})
        else:
            doabort("BAD_REQ", "No Op Specified")
    else:
        doabort("BAD_REQ", "GET not supported")


#function to add a user to a library.
#TODO: do we want a useras here? 
def addMemberToPostable(g, request, fqpn):#fqmn/[changerw]
    jsonpost=dict(request.json)
    fqmn=_dictp('member', jsonpost)
    changerw=_dictp('changerw', jsonpost)
    if not changerw:
        changerw=False
    user, postable=g.db.addMemberableToMembable(g.currentuser, g.currentuser, fqpn, fqmn, changerw)
    #print "here"
    return user, postable

def getMembersOfMembable(g, request, fqpn):
    useras=g.currentuser
    users=g.db.membersOfMembableFromFqin(g.currentuser,useras,fqpn)
    userdict={'users':users}
    return userdict

def getInvitedsForMembable(g, request, fqpn):
    useras=g.currentuser
    users=g.db.invitedsForMembableFromFqin(g.currentuser,useras,fqpn)
    userdict={'users':users}
    return userdict

@adsgut.route('/group/<groupowner>/group:<groupname>/inviteds')
def groupInviteds(groupowner, groupname):
    fqgn=groupowner+"/group:"+groupname
    userdict=getInvitedsForMembable(g, request, fqgn)
    return jsonify(userdict)

@adsgut.route('/library/<libraryowner>/library:<libraryname>/inviteds')
def libraryInviteds(libraryowner, libraryname):
    fqln=libraryowner+"/library:"+libraryname
    userdict=getInvitedsForMembable(g, request, fqln)
    return jsonify(userdict)

#add user to group, or get members
@adsgut.route('/group/<groupowner>/group:<groupname>/members', methods=['GET', 'POST'])#fqmn/[changerw]
def addMembertoGroup_or_groupMembers(groupowner, groupname):
    #add permit to match user with groupowner
    fqgn=groupowner+"/group:"+groupname
    if request.method == 'POST':
        member, group=addMemberToPostable(g, request, fqgn)
        return jsonify({'status':'OK', 'info': {'member':member.basic.fqin, 'type':'group', 'postable':group.basic.fqin}})
    else:
        userdict=getMembersOfMembable(g, request, fqgn)
        return jsonify(userdict)

#add user to app, or get members
@adsgut.route('/app/<appowner>/app:<appname>/members', methods=['GET', 'POST'])#fqmn/[changerw]
def addMemberToApp_or_appMembers(appowner, appname):
    #add permit to match user with groupowner
    fqan=appowner+"/app:"+appname
    if request.method == 'POST':
        member, app=addMemberToPostable(g, request, fqan)
        return jsonify({'status':'OK', 'info': {'member':member.basic.fqin, 'type':'app', 'postable':app.basic.fqin}})
    else:
        userdict=getMembersOfMembable(g, request, fqan)
        return jsonify(userdict)


#add user or group to library, (but we use next one actually). we do use this for members
@adsgut.route('/library/<libraryowner>/library:<libraryname>/members', methods=['GET', 'POST'])#fqmn/[changerw]
def addMemberToLibrary_or_libraryMembers(libraryowner, libraryname):
    #add permit to match user with groupowner
    fqln=libraryowner+"/library:"+libraryname
    if request.method == 'POST':
        member, library=addMemberToPostable(g, request, fqln)
        return jsonify({'status':'OK', 'info': {'member':member.basic.fqin, 'type':'library', 'postable':library.basic.fqin}})
    else:
        userdict=getMembersOfMembable(g, request, fqln)
        return jsonify(userdict)


#add memberable to postable(library)
#Only currently used to add a group toa library, but could be used to add users. But we
#always invite users. Bulk can use a script anyways.
@adsgut.route('/postable/<po>/<pt>:<pn>/members', methods=['GET', 'POST'])#fqmn/[changerw]
def addMemberToPostable_or_postableMembers(po, pt, pn):
    fqpn=po+"/"+pt+":"+pn
    if request.method == 'POST':
        member, postable=addMemberToPostable(g, request, fqpn)
        dictis = {'status':'OK', 'info': {'member':member.basic.fqin, 'type':pt, 'postable':postable.basic.fqin}}
        return jsonify(dictis)
    else:
        userdict=getMembersOfMembable(g, request, fqpn)
        return jsonify(userdict)

#remove a member(user/group) from a group/app/library. The user doing it could be the member
#or could be the owner of the membable
@adsgut.route('/memberremove', methods=['POST'])
def memberremove():#useras/member/gqpn
    if request.method=='POST':
        jsonpost=dict(request.json)
        fqpn = _dictp('fqpn', jsonpost)
        useras = _userpostget(g, jsonpost)
        member = _dictp('member', jsonpost)
        if fqpn is None:
            doabort("BAD_REQ", "No postable specified for member removal")
        g.db.removeMemberableFromMembable(g.currentuser, useras, fqpn, member)
        return jsonify({'status':'OK'})

#this will delete a group or a library. need owner user and fqpn of group/library.
@adsgut.route('/membableremove', methods=['POST'])
def membableremove():#useras/fqpn
    if request.method=='POST':
        jsonpost=dict(request.json)
        fqpn = _dictp('fqpn', jsonpost)
        useras = _userpostget(g, jsonpost)
        if fqpn is None:
            doabort("BAD_REQ", "No membable specified for  removal")
        g.dbp.removeMembable(g.currentuser, useras, fqpn)
        return jsonify({'status':'OK'})

#######################################################################################################################
#The next few return individual group and library profiles. The Info functions are web services used in the profile page
#######################################################################################################################

#return information about the group or library. the world postable is a misnomer for now.
#this is a common function used in the web services below
def postable(ownernick, name, ptstr):
    fqpn=ownernick+"/"+ptstr+":"+name
    postable, owner, creator=g.db.getMembableInfo(g.currentuser, g.currentuser, fqpn)
    isowner=False
    if g.db.isOwnerOfPostable(g.currentuser, g.currentuser, postable):
        isowner=True
    postablesin=g.currentuser.postablesin
    rw=False
    for p in postablesin:
        if p.fqpn==postable.basic.fqin:
            rw=p.readwrite
    return postable, isowner, rw, owner.presentable_name(), creator.presentable_name()


#get group info
@adsgut.route('/group/<groupowner>/group:<groupname>')
def groupInfo(groupowner, groupname):
    g, io, rw, on, cn = postable(groupowner, groupname, "group")
    return jsonify(group=g, oname = on, cname = cn, io=io, rw=rw)

#get group profile
@adsgut.route('/postable/<groupowner>/group:<groupname>/profile/html')
def groupProfileHtml(groupowner, groupname):
    return profileHtmlNotRouted(groupowner, groupname, "group", inviteform=None)


#get app info
@adsgut.route('/app/<appowner>/app:<appname>')
def appInfo(appowner, appname):
    a, io, rw, on, cn = postable(appowner, appname, "app")
    return jsonify(app=a, oname = on, cname = cn, io=io, rw=rw)

#get app profile, not used currently
@adsgut.route('/postable/<appowner>/app:<appname>/profile/html')
def appProfileHtml(appowner, appname):
    return profileHtmlNotRouted(appowner, appname, "app", inviteform=None)


#get library info
@adsgut.route('/library/<libraryowner>/library:<libraryname>')
def libraryInfo(libraryowner, libraryname):
    l, io, rw, on, cn = postable(libraryowner, libraryname, "library")
    return jsonify(library=l, oname=on, cname=cn, io=io, rw=rw)

#get library profile
@adsgut.route('/postable/<libraryowner>/library:<libraryname>/profile/html')
def libraryProfileHtml(libraryowner, libraryname):
    return profileHtmlNotRouted(libraryowner, libraryname, "library", inviteform=None)

#general function used above which gets the right flask-wtf form for recaptcha for invitations
def profileHtmlNotRouted(powner, pname, ptype, inviteform=None):
    p, owner, rw, on, cn=postable(powner, pname, ptype)
    if not inviteform:
      if ptype=="library":
        inviteform = InviteForm()
      else:
        inviteform = InviteFormGroup()
    return render_template(ptype+'profile.html', thepostable=p, owner=owner, rw=rw, inviteform=inviteform, useras=g.currentuser, po=powner, pt=ptype, pn=pname)


#this is the workhorse for displaying items, for any library
@adsgut.route('/postable/<po>/<pt>:<pn>/filter/html')
def postableFilterHtml(po, pt, pn):
    querystring=request.query_string
    p, owner, rw, on, cn=postable(po, pn, pt)
    pflavor='pos'
    if pn=='public' and po=='adsgut' and pt=='library':
        pflavor='pub'
    if pn=='default' and pt=='library':
        tqtype='stags'
        pflavor='udg'#even though this is now a library, we still call it udg in js code
    else:
        pflavor=p.basic.fqin
        tqtype='tagname'
    tqtype='tagname'
    return render_template('postablefilter.html', p=p, po=po, pt=pt, pn=pn, pflavor=pflavor, querystring=querystring, tqtype=tqtype, useras=g.currentuser, owner=owner, rw=rw)

#get the user defaukt library's items
@adsgut.route('/postable/<nick>/library:default/filter/html')
def udlHtml(nick):
    return postableFilterHtml(nick, "library", "default")

#get the user default library from email
@adsgut.route('/postablefromadsid/<adsid>/library:default/filter/html')
def udlHtmlFromAdsid(adsid):
    user=g.db.getUserInfoFromAdsid(g.currentuser, adsid)
    return postableFilterHtml(user.nick, "library", "default")

#get the public library. The public group's library is not displayed at this moment
@adsgut.route('/postable/adsgut/library:public/filter/html')
def publicHtml():
    return postableFilterHtml("adsgut", "library", "public")


#######################################################################################################################
#The next bunch are all for items and tags
#######################################################################################################################

#contexts are not currently used, so this is greyed out
# def _getContext(q):
#     #BUG:user contexts will be hidden. So this will change
#     if not q.has_key('cuser'):
#         return None
#     context={}
#     if q['cuser']=="True":
#         context['user']=True
#     else:
#         context['user']=False
#     if not q.has_key('ctype'):
#         return None
#     context['type']=q['ctype']
#     if not q.has_key('cvalue'):
#         return None
#     context['value']=q['cvalue']
#     return context



#The users simple tags, not singletonmode (ie no notes)
@adsgut.route('/user/<nick>/tagsuserowns')
def tagsUserOwns(nick):
    query=dict(request.args)
    useras, usernick=_userget(g, query)
    tagtype= _dictg('tagtype', query)
    stags=g.dbp.getTagsAsOwnerOnly(g.currentuser, useras, tagtype)
    stagdict={'simpletags':set([e.basic.name for e in stags[1]])}
    return jsonify(stagdict)

#these are the simple tags user owns as well as can write to by dint of being in a library
#or by being in a group which is a member of the tag. group membership of tags is not yet
#implemented, but the idea is for groups to come up with their own vocabulary systems
@adsgut.route('/user/<nick>/tagsusercanwriteto')
def tagsUserCanWriteTo(nick):
    query=dict(request.args)
    useras, usernick=_userget(g, query)
    tagtype= _dictg('tagtype', query)
    fqpn = _dictg('fqpn',query)
    stags=g.dbp.getAllTagsForUser(g.currentuser, useras, tagtype, False, fqpn)
    stagdict={'simpletags':set([e.basic.name for e in stags[1]])}
    return jsonify(stagdict)

#this is only those tags obtained from membership in libs. Not currently used.
@adsgut.route('/user/<nick>/tagsasmember')
def tagsUserAsMember(nick):
    query=dict(request.args)
    useras, usernick=_userget(g, query)
    tagtype= _dictg('tagtype', query)
    fqpn = _dictg('fqpn',query)
    stags=g.dbp.getTagsAsMemberOnly(g.currentuser, useras, tagtype, False, fqpn)
    stagdict={'simpletags':set([e.basic.name for e in stags[1]])}
    return jsonify(stagdict)

########################


#################now going to tags and item posts#################################


#POST posts items into postable, GET gets items for postable consistent with user.
#all items in post must be of same type
#this is the workhorse function for the library items page
#the tags areimplicitly obtained through the posting document
@adsgut.route('/postable/<po>/<pt>:<pn>/items', methods=['GET', 'POST'])#user/items/itemtype
def itemsForPostable(po, pt, pn):
    if request.method=='POST':
        jsonpost=dict(request.json)
        useras = _userpostget(g, jsonpost)
        #get a list of 'names'(bibcodes) for the itemtype (pubs)
        items = _itemspostget(jsonpost)
        #also get the itemtypr
        itemtype=_dictp('itemtype', jsonpost)
        fqpn=po+"/"+pt+":"+pn
        pds=[]
        #save the items and put them into the library
        for name in items:
            itemspec={'name':name, 'itemtype':itemtype}
            i=g.dbp.saveItem(g.currentuser, useras, itemspec)
            i,pd=g.dbp.postItemIntoPostable(g.currentuser, useras, fqpn, i)
            pds.append(pd)
        #if this works send the posting documents back. note this will include
        #others posts in pd.hist but they are all in this library so there is no leakage
        itempostings={'status':'OK', 'postings':pds, 'postable':fqpn}
        return jsonify(itempostings)
    else:
        query=dict(request.args)
        useras, usernick=_userget(g, query)
        #get user, sort, and pagetuple. with user, also get if u only want that user's posts
        #otheerwise the useras is used to make sure the user has the righ permissions
        sort = _sortget(query)
        pagtuple = _pagtupleget(query)
        #criteria is used for further filtering (currently not used)
        criteria= _criteriaget(query)
        postable= po+"/"+pt+":"+pn
        q=_queryget(query)
        #Add the postable wanted to the query. The query q is used to get
        #tagtypes and tagnames if wanted
        if not q.has_key('postables'):
            q['postables']=[]
        q['postables'].append(postable)
        #print "Q is", q, query, useras, usernick
        #By this time query is popped down
        count, items=g.dbp.getItemsForQuery(g.currentuser, useras,
            q, usernick, criteria, sort, pagtuple)
        return jsonify({'items':items, 'count':count, 'postable':postable})

#same as above but only GET and is used to get json
#the one difference is that we get the tags along the way explicitly
@adsgut.route('/postable/<po>/<pt>:<pn>/json', methods=['GET'])
def jsonItemsForPostable(po, pt, pn):
    query=dict(request.args)
    useras, usernick=_userget(g, query)

    sort = _sortget(query)
    pagtuple = _pagtupleget(query)
    criteria= _criteriaget(query)
    postable= po+"/"+pt+":"+pn
    q=_queryget(query)
    if not q.has_key('postables'):
        q['postables']=[]
    q['postables'].append(postable)
    count, items=g.dbp.getItemsForQueryWithTags(g.currentuser, useras,
        q, usernick, criteria, sort, pagtuple)
    return jsonify({'items':items, 'count':count, 'postable':postable})

#same as above but for csv
@adsgut.route('/postable/<po>/<pt>:<pn>/csv', methods=['GET'])
def csvItemsForPostable(po, pt, pn):
    query=dict(request.args)
    useras, usernick=_userget(g, query)
    sort = _sortget(query)
    pagtuple = _pagtupleget(query)
    #pagtuple=(2,1)
    criteria= _criteriaget(query)
    postable= po+"/"+pt+":"+pn
    q=_queryget(query)
    if not q.has_key('postables'):
        q['postables']=[]
    q['postables'].append(postable)
    count, items=g.dbp.getItemsForQueryWithTags(g.currentuser, useras,
        q, usernick, criteria, sort, pagtuple)
    #Take the result and convert it into a CSV format
    csvstring="#count="+str(count)+",postable="+postable+"\n"
    for i in items:
        s=i['basic']['name']
        for t in i['tags']:
            l=s+","+t
            csvstring=csvstring+l+"\n"
        if len(i['tags'])==0:
            csvstring=csvstring+s+",\n"
    return Response(csvstring, mimetype='text/csv')


#just specialized to library
@adsgut.route('/library/<libraryowner>/library:<libraryname>/items')
def libraryItems(libraryowner, libraryname):
    return itemsForPostable(libraryowner, "library", libraryname)


#the POST is used to post an item-tag pair into a postable
#the GET gets the taggings for a query in a postable
#TODO: more docs needed. Do not believe this is currently used

@adsgut.route('/postable/<po>/<pt>:<pn>/taggings', methods=['GET', 'POST'])
def taggingsForPostable(po, pt, pn):
    if request.method=='POST':
        jsonpost=dict(request.json)
        useras = _userpostget(g, jsonpost)
        itemsandtags = _itemstagspostget(jsonpost)
        fqpn=po+"/"+pt+":"+pn
        tds=[]
        for d in itemsandtags:
            fqin=d['fqin']
            fqtn=d['fgtn']
            td=g.dbp.getTaggingDoc(g.currentuser, useras, fqin, fqtn)
            i,t,td=g.dbp.postTaggingIntoPostable(g.currentuser, useras, fqpn, td)
            tds.append(td)
        itemtaggings={'status':'OK', 'taggings':tds, 'postable':fqpn}
        return jsonify(itemtaggings)
    else:
        query=dict(request.args)
        useras, usernick=_userget(g, query)

        #need to pop the other things like pagetuples etc. Helper funcs needed
        sort = _sortget(query)
        criteria= _criteriaget(query)
        postable= po+"/"+pt+":"+pn
        q=_queryget(query)
        if not q.has_key('postables'):
            q['postables']=[]
        q['postables'].append(postable)
        #By this time query is popped down
        count, taggings=g.dbp.getTaggingsForQuery(g.currentuser, useras,
            q, usernick, criteria, sort)
        return jsonify({'taggings':taggings, 'count':count, 'postable':postable})

#GET all tags consistent with user for a particular postable and further query
#this is a workhorse function which populates the lhs set of tags
@adsgut.route('/postable/<po>/<pt>:<pn>/tags', methods=['GET'])
def tagsForPostable(po, pt, pn):
    query=dict(request.args)
    useras, usernick=_userget(g, query)
    #criteria currently unused
    criteria= _criteriaget(query)
    postable= po+"/"+pt+":"+pn
    #tagnames and tagtypes used in query to get only those tags compatible with the tag used
    #this is used for filtering in the user interface
    q=_queryget(query)
    if not q.has_key('postables'):
        q['postables']=[]
    if pt=='library' and pn=='default':#in saved items get from all postables(libraries) we are in
        #i believe this is currently done in the downstream function
        q['postables'].append(postable)
    else:
        q['postables'].append(postable)

    count, tags=g.dbp.getTagsForQueryFromPostingDocs(g.currentuser, useras,
        q, usernick, criteria)
    return jsonify({'tags':tags, 'count':count})


#remove items from library
@adsgut.route('/itemsremove', methods=['POST'])#fqpn/itemsto remove/user
def itemsremove():
    if request.method=='POST':
        jsonpost=dict(request.json)
        fqpn = _dictp('fqpn', jsonpost)
        useras = _userpostget(g, jsonpost)
        items = _itemspostget(jsonpost)
        if fqpn is None:
            doabort("BAD_REQ", "No postable specified for item removal")
        for itemfqin in items:
            g.dbp.removeItemFromPostable(g.currentuser, useras, fqpn, itemfqin)
        return jsonify({'status':'OK', 'info':items})

#POST saveItems(s), this is used in the posting form under 'export'
#GET could take a bunch of items as arguments, or a query
#I dont believe GET is used. TODO: we should perhaps suppress the GET
@adsgut.route('/items', methods=['POST', 'GET'])
def items():
    ##useras?/name/itemtype
    #q={useras?, userthere?, sort?, pagetuple?, criteria?, stags|tagnames ?, postables?}
    if request.method=='POST':
        jsonpost=dict(request.json)
        useras = _userpostget(g, jsonpost)
        creator=useras.basic.fqin
        items = _itemspostget(jsonpost)
        itemtype = _dictp('itemtype', jsonpost)
        if not itemtype:
            doabort("BAD_REQ", "No itemtype specified for item")
        for name in items:
            itspec={'creator':creator, 'name':name, 'itemtype':itemtype}
            newitem=g.dbp.saveItem(g.currentuser, useras, itspec)
        return jsonify({'status':'OK', 'info':items})
    else:
        query=dict(request.args)
        useras, usernick=_userget(g, query)
        #query stuff
        sort = _sortget(query)
        pagtuple = _pagtupleget(query)
        criteria= _criteriaget(query)
        #By this time query is popped down
        count, items=g.dbp.getItemsForQuery(g.currentuser, useras,
            query, usernick, criteria, sort, pagtuple)
        return jsonify({'items':items, 'count':count})

#POST: create a new tag
#GET get tags for query
#currently unused. TODO: perhaps GET should be suppressed
#this is currently unused as we dont allow for free form creation of tags
#but this might be useful at some point in the future for vocabulary creation
@adsgut.route('/tags', methods=['POST', 'GET'])
def tags():
    if request.method=='POST':
        jsonpost=dict(request.json)
        useras = _userpostget(g, jsonpost)
        tagspecs=_tagspecspostget(jsonpost)
        newtags=[]
        for ti in tagspecs['tags']:
            if not ti.has_key('name'):
                doabort('BAD_REQ', "No name specified for tag")
            if not ti.has_key('tagtype'):
                doabort('BAD_REQ', "No tagtypes specified for tag")
            tagspec={}
            tagspec['creator']=useras.basic.fqin
            if ti.has_key('name'):
                tagspec['name'] = ti['name']
            tagspec['tagtype'] = ti['tagtype']
            t=g.dbp.makeTag(g.currentuser, useras, tagspec)
            newtags.append(t)

        tags={'status':'OK', 'info':{'item': i.basic.fqin, 'tags':[td for td in newtags]}}
        return jsonify(tags)
    else:
        query=dict(request.args)
        useras, usernick=_userget(g, query)

        criteria= _criteriaget(query)
        count, tags=g.dbp.getTagsForQuery(g.currentuser, useras,
            query, usernick, criteria)
        return jsonify({'tags':tags, 'count':count})


#sets up the tag spec to tag an item
def _setupTagspec(ti, useras):
    #atleast one of name or content must be there (tag or note)
    if not (ti.has_key('name') or ti.has_key('content')):
        doabort('BAD_REQ', "No name or content specified for tag")
    if not ti['tagtype']:
        doabort('BAD_REQ', "No tagtypes specified for tag")
    tagspec={}
    tagspec['creator']=useras.basic.fqin
    if ti.has_key('name'):
        tagspec['name'] = ti['name']
    if ti.has_key('tagmode'):
        tagspec['tagmode'] = ti['tagmode']
    if ti.has_key('content'):
        tagspec['content'] = ti['content']
    tagspec['tagtype'] = ti['tagtype']
    return tagspec

#GET tags for an item 
#or POST: tag an item

@adsgut.route('/tags/<ns>/<itemname>', methods=['GET', 'POST'])
def tagsForItem(ns, itemname):
    ifqin=ns+"/"+itemname
    if request.method == 'POST':
        jsonpost=dict(request.json)
        useras = _userpostget(g, jsonpost)
        itemtype=_dictp('itemtype', jsonpost)
        itemspec={'name':itemname, 'itemtype':itemtype}
        #we use the fqpn to get the return to only get tags consistent with a certain library
        fqpn = _dictp('fqpn',jsonpost)
        #save the item if not saved already (we dont use this tho)
        i=g.dbp.saveItem(g.currentuser, useras, itemspec)
        #get the tag specs
        tagspecs=_tagspecspostget(jsonpost)
        newtaggings=[]
        if not tagspecs.has_key(itemname):
            doabort('BAD_REQ', "No itemname specified to tag")
        for ti in tagspecs[itemname]:
            tagspec=_setupTagspec(ti, useras)
            i,t,it,td=g.dbp.tagItem(g.currentuser, useras, i, tagspec)
            newtaggings.append(td)
        #get ALL the taggings consistent with this item and this user back
        taggingsdict, taggingsthispostable, taggingsdefault= g.dbp.getTaggingsConsistentWithUserAndItems(g.currentuser, useras, [ifqin], None, fqpn)
        return jsonify(fqpn=fqpn, taggings=taggingsdict, taggingtp=taggingsthispostable, taggingsdefault=taggingsdefault)
    else:
        query=dict(request.args)
        useras, usernick=_userget(g, query)

        sort = _sortget(query)
        fqpn = _dictg('fqpn',query)
        taggingsdict, taggingsthispostable, taggingsdefault= g.dbp.getTaggingsConsistentWithUserAndItems(g.currentuser, useras, [ifqin], sort, fqpn)
        return jsonify(fqpn=fqpn, taggings=taggingsdict, taggingtp=taggingsthispostable, taggingsdefault=taggingsdefault)

#remove a tag from an item, for a particular library.
@adsgut.route('/tagsremove/<ns>/<itemname>', methods=['POST'])
def tagsRemoveForItem(ns, itemname):
    ifqin=ns+"/"+itemname
    if request.method == 'POST':
        jsonpost=dict(request.json)
        useras = _userpostget(g, jsonpost)
        tagname=_dictp('tagname', jsonpost)
        tagtype=_dictp('tagtype', jsonpost)
        fqpn = _dictp('fqpn',jsonpost)
        fqtn = _dictp('fqtn',jsonpost)
        #will use useras for the namespace if it is removing your own stuff
        #for a library owner removing a tag 'viagra' the full fqtn is needed
        if fqtn==None:#nothing was sent over the wire
            fqtn = useras.nick+'/'+tagtype+":"+tagname

        if fqpn==None:#nuke it, this happens for saved items (for private notes too)
          val=g.dbp.untagItem(g.currentuser, useras, fqtn, ifqin)
        else:#remove tag from postable (should only affect pinpostables)
          val=g.dbp.removeTaggingFromPostable(g.currentuser, useras, fqpn, ifqin, fqtn)
        taggingsdict, taggingsthispostable, taggingsdefault= g.dbp.getTaggingsConsistentWithUserAndItems(g.currentuser, useras, [ifqin], None, fqpn)
        return jsonify(fqpn=fqpn, taggings=taggingsdict, taggingtp=taggingsthispostable, taggingsdefault=taggingsdefault)


#GET is used to get the taggings consistent with user for a set of items (unused currently)
#POST used in postform to tag items without worrying about library (will go in default library)
#notice no fqpn here, since we dont care for the library
#this function is used in the postform interface
@adsgut.route('/items/taggings', methods=['POST', 'GET'])#items/itemtype/tagspecs/user
def itemsTaggings():
    if request.method=='POST':
        jsonpost=dict(request.json)
        useras = _userpostget(g, jsonpost)
        items = _itemspostget(jsonpost)
        tagspecs=_tagspecspostget(jsonpost)
        itemtype=_dictp('itemtype', jsonpost)
        newtaggings=[]
        for name in items:
            itemspec={'name':name, 'itemtype':itemtype}
            i=g.dbp.saveItem(g.currentuser, useras, itemspec)
            if not tagspecs.has_key(name):
                doabort('BAD_REQ', "No itemname specified to tag")
            for ti in tagspecs[name]:
                tagspec=_setupTagspec(ti, useras)
                i,t,it,td=g.dbp.tagItem(g.currentuser, useras, i, tagspec)
                newtaggings.append(td)
        taggingsdict,_,junk=g.dbp.getTaggingsConsistentWithUserAndItems(g.currentuser, useras,
            items, None)
        return jsonify(taggings=taggingsdict)
    else:
        query=dict(request.args)
        useras, usernick=_userget(g, query)
        sort = _sortget(query)
        items = _itemsget(query)
        taggingsdict,_,junk=g.dbp.getTaggingsConsistentWithUserAndItems(g.currentuser, useras,
            items, sort)
        return jsonify(taggings=taggingsdict)

#POST: usedin postform to post items into a postable
#GET: just get the consistent postings
@adsgut.route('/items/postings', methods=['POST', 'GET'])
def itemsPostings():
    if request.method=='POST':
        jsonpost=dict(request.json)
        useras = _userpostget(g, jsonpost)
        items = _itemspostget(jsonpost)
        fqpo = _postablesget(jsonpost)
        itemtype=_dictp('itemtype', jsonpost)
        pds=[]
        for name in items:
            itemspec={'name':name, 'itemtype':itemtype}
            i=g.dbp.saveItem(g.currentuser, useras, itemspec)
            for fqpn in fqpo:
                i,pd=g.dbp.postItemIntoPostable(g.currentuser, useras, fqpn, i)
                pds.append(pd)
        #return consistent postings for the user
        postingsdict=g.dbp.getPostingsConsistentWithUserAndItems(g.currentuser, useras,
            items, None)
        return jsonify(postings=postingsdict)
    else:
        query=dict(request.args)
        useras, usernick=_userget(g, query)
        sort = _sortget(query)
        items = _itemsget(query)
        postingsdict=g.dbp.getPostingsConsistentWithUserAndItems(g.currentuser, useras,
            items, sort)
        return jsonify(postings=postingsdict)

#both POST and GET are used to get taggings and postings for a set of items
#this is the one used in the filter interface
#currently used for all items
#to make faster we must put in pagination
@adsgut.route('/items/taggingsandpostings', methods=['POST', 'GET'])#user/fqpn/items
def itemsTaggingsAndPostings():
    if request.method=='POST':
        #"THIS WILL NOT BE TO POST STUFF IN BUT TO GET RESULTS"
        jsonpost=dict(request.json)
        useras = _userpostget(g, jsonpost)
        sort = _sortpostget(jsonpost)
        items = _itemspostget(jsonpost)
        fqpn = _dictp('fqpn',jsonpost)
        postingsdict=g.dbp.getPostingsConsistentWithUserAndItems(g.currentuser, useras, items, sort)
        taggingsdict, taggingsthispostable, taggingsdefault=g.dbp.getTaggingsConsistentWithUserAndItems(g.currentuser, useras, items, sort, fqpn)
        return jsonify(fqpn=fqpn, postings=postingsdict, taggings=taggingsdict, taggingtp=taggingsthispostable, taggingsdefault=taggingsdefault)
    else:
        query=dict(request.args)
        useras, usernick=_userget(g, query)
        sort = _sortget(query)
        items = _itemsget(query)
        fqpn = _dictg('fqpn',query)
        postingsdict=g.dbp.getPostingsConsistentWithUserAndItems(g.currentuser, useras,
            items, sort)
        taggingsdict, taggingsthispostable, taggingsdefault=g.dbp.getTaggingsConsistentWithUserAndItems(g.currentuser, useras,
            items, sort, fqpn)
        return jsonify(fqpn=fqpn, postings=postingsdict, taggings=taggingsdict, taggingtp=taggingsthispostable, taggingsdefault=taggingsdefault)


#add or get an itemtype. currently not used, we do this in python code
@adsgut.route('/itemtypes', methods=['POST', 'GET'])
def itemtypes():
    if request.method=='POST':
        jsonpost=dict(request.json)
        useras = _userpostget(g, jsonpost)
        itspec={}
        itspec['creator']=useras.basic.fqin
        itspec['name'] = _dictp('name', jsonpost)
        if not itspec['name']:
            doabort("BAD_REQ", "No name specified for itemtype")
        itspec['postable'] = _dictp('postable', jsonpost)
        if not itspec['postable']:
            doabort("BAD_REQ", "No postable specified for itemtype")
        newitemtype=g.dbp.addItemType(g.currentuser, useras, itspec)
        return jsonify({'status':'OK', 'info':newitemtype})
    else:
        query=dict(request.args)
        useras, usernick=_userget(g, query)
        criteria= _criteriaget(query)
        isitemtype=True
        count, thetypes=g.dbp.getTypesForQuery(g.currentuser, useras, criteria, usernick, isitemtype)
        return jsonify({'types':thetypes, 'count':count})

#add or get an tagtype. currently not used, we do this in python code
@adsgut.route('/tagtypes', methods=['POST', 'GET'])
def tagtypes():
    ##useras?/name/itemtype
    #q={useras?, userthere?, sort?, pagetuple?, criteria?, stags|tagnames ?, postables?}
    if request.method=='POST':
        jsonpost=dict(request.json)
        useras = _userpostget(g, jsonpost)
        itspec={}
        itspec['creator']=useras.basic.fqin
        itspec['name'] = _dictp('name', jsonpost)
        itspec['tagmode'] = _dictp('tagmode', jsonpost)
        itspec['singletonmode'] = _dictp('singletonmode',jsonpost)
        if not itspec['tagmode']:
            del itspec['tagmode']
        else:
            itspec['tagmode']=bool(itspec['tagmode'])
        if not itspec['singletonmode']:
            del itspec['singletonmode']
        else:
            itspec['singletonmode']=bool(itspec['singletonmode'])
        if not itspec['name']:
            doabort("BAD_REQ", "No name specified for itemtype")
        itspec['postable'] = _dictp('postable', jsonpost)
        if not itspec['postable']:
            doabort("BAD_REQ", "No postable specified for itemtype")
        newtagtype=g.dbp.addTagType(g.currentuser, useras, itspec)
        return jsonify({'status':'OK', 'info':newtagtype})
    else:
        query=dict(request.args)
        useras, usernick=_userget(g, query)
        criteria= _criteriaget(query)
        isitemtype=False
        count, thetypes=g.dbp.getTypesForQuery(g.currentuser, useras, criteria, usernick, isitemtype)
        return jsonify({'types':thetypes, 'count':count})

#this is just a function to split up an itemstring. used in postform
#should be replaced by an internal function:this is kind of stupid
#(atleast POST is used there)
@adsgut.route('/itemsinfo', methods = ['POST', 'GET'])
def itemsinfo():
    if request.method=='POST':
        jsonpost=dict(request.json)
        itemstring=jsonpost.get('items',[''])
        items=itemstring.split(':')
        #print "LLLL", itemstring, items
        theitems=[{'basic':{'name':i.split('/')[-1], 'fqin':i}} for i in items]
    else:
        query=dict(request.args)
        itemstring=query.get('items',[''])[0]
        items=itemstring.split(':')
        theitems=[{'basic':{'name':i.split('/')[-1], 'fqin':i}} for i in items]
    return jsonify({'items': theitems, 'count':len(theitems)})

from config import config

#A POST to set up the postform in html. It works from the export menu
#gets the bibcodes, uses a bigquery solr request to populate the titles
@adsgut.route('/postform/<itemtypens>/<itemtypename>/html', methods=['POST'])
def postForm(itemtypens, itemtypename):
    qstring=""
    itemtype=itemtypens+"/"+itemtypename
    if request.method=='POST':
        if itemtype=="ads/pub":
            current_page=request.referrer
            if request.values.has_key('numRecs'):
                numrecs = request.values.get('numRecs')
            else:
                numrecs = config.SEARCH_DEFAULT_ROWS
            if request.values.has_key('bibcode'):
                bibcodes = request.values.getlist('bibcode')
            else:
                try:
                    query_components = json.loads(request.values.get('current_search_parameters'))
                except:
                    return render_template('errors/generic_error.html', error_message='Error. Please try later.')

                #update the query parameters to return only what is necessary
                query_components.update({
                    'facets': [],
                    'fields': ['bibcode'],
                    'highlights': [],
                    'rows': str(numrecs)
                    })

                list_type = request.values.get('list_type')
                if 'sort' not in query_components:
                    from adsabs.core.solr.query_builder import create_sort_param
                    query_components['sort'] = create_sort_param(list_type=list_type)

                req = solr.create_request(**query_components)
                if 'bigquery' in request.values:
                    from adsabs.core.solr import bigquery
                    bigquery.prepare_bigquery_request(req, request.values['bigquery'])
                req = solr.set_defaults(req)
                resp = solr.get_response(req)
                #return error if solr messes up
                if resp.is_error():
                    return render_template('errors/generic_error.html', error_message='Error while loading bibcodes for posting. Please try later.')

                bibcodes = [x.bibcode for x in resp.get_docset_objects()]
            items=["ads/"+i for i in bibcodes]
        elif itemtype=="ads/search":#not implemented yet
            itemstring=query.get('items',[''])[0]
    
        theitems=[]
        if itemtype=="ads/pub":
            theitems=[{ 'basic':{'name':i.split('/')[-1],'fqin':i}} for i in items]
        elif itemtype=="ads/search":#not implemented yet
            theitems=[{ 'basic':{'name':itemstring,'fqin':'ads/'+itemstring}}]
        #if only one item we allow notes as yet
        singlemode=False
        if len(theitems) ==1:
            singlemode=True
        nameable=False
        if itemtype=="ads/pub":
            qstring=":".join(items)
        elif itemtype=="ads/search":
            nameable=True
            qstring=itemstring
        if nameable and singlemode:
            nameable=True

        return render_template('postform_fancy.html', items=theitems,
            querystring=qstring,
            singlemode=singlemode,
            nameable=nameable,
            itemtype=itemtypename,
            curpage=current_page,
            useras=g.currentuser)



#making the import:
#TODO:make sure this gets into the config
#ADS_CLASSIC_LIBRARIES_URL = config.ADS_CLASSIC_LIBRARIES_URL
ADS_CLASSIC_LIBRARIES_URL = "http://adsabs.harvard.edu/cgi-bin/maint/export_privlib"
import requests

def perform_classic_library_query(parameters, headers, service_url):
    """
    function that performs a get request and returns a json object
    """
    #Perform the request
    r = requests.get(service_url, params=parameters, headers=headers)
    #Check for problems
    try:
        r.raise_for_status()
    except Exception, e:
        exc_info = sys.exc_info()
        app.logger.error("Author http request error: %s, %s\n%s" % (exc_info[0], exc_info[1], traceback.format_exc()))
        doabort("SRV_ERR", "Somewhing went wrong in contacting classic server")
    try:
        user_json = r.json()
    except Exception, e:
        exc_info = sys.exc_info()
        app.logger.error("Author JSON decode error: %s, %s\n%s" % (exc_info[0], exc_info[1], traceback.format_exc()))
        r = None
        user_json = {}
    return user_json

#make a query to bigquery to the title, author, etc
def perform_solr_bigquery(bibcodes):
    """
    function that performs a POST request and returns a json object
    """
    headers = {'Content-Type': 'big-query/csv'}
    url=config.SOLRQUERY_URL
    qdict = {
        'q':'text:*:*',
        'fq':'{!bitset compression=none}',
        'wt':'json',
        'fl':'bibcode,title,pubdate,author'
    }
    #Perform the request
    qdict['rows']=len(bibcodes)
    rstr = "bibcode\n"+"\n".join(bibcodes)
    r = requests.post(url, params=qdict, data=rstr, headers=headers)
    #Check for problems
    try:
        r.raise_for_status()
    except Exception, e:
        exc_info = sys.exc_info()
        app.logger.error("Author http request error: %s, %s\n%s" % (exc_info[0], exc_info[1], traceback.format_exc()))

    try:
        d = r.json()
    except Exception, e:
        exc_info = sys.exc_info()
        app.logger.error("Author JSON decode error: %s, %s\n%s" % (exc_info[0], exc_info[1], traceback.format_exc()))
        r = None
        d = {}
    return d

#Use GET to get the classic libraries. TODO: make this POST as its destructive BUG
@adsgut.route('/classic/<cookieid>/libraries', methods=['GET'])
def get_classic_libraries(cookieid, password=None):

    headers = {'User-Agent':'ADS Script Request Agent'}
    parameters = {'cookie':cookieid}
    try:
        libjson=perform_classic_library_query(parameters, headers, ADS_CLASSIC_LIBRARIES_URL)
    except:
        #import sys
        #print ">>>", sys.exc_info()
        doabort("SRV_ERR", "Somewhing went wrong in contacting classic server")
    useras=g.db._getUserForCookieid(g.currentuser, cookieid)
    useras.classicimported=True
    useras.save(safe=True)
    ret=g.dbp.populateLibraries(g.currentuser, useras, libjson)
    if ret:
        return redirect(url_for('adsgut.userProfileHtml', nick=useras.nick))
    else:
        return redirect('/')

#for a list of bibcodes, get bibquery results
@adsgut.route('/bigquery/bibcodes', methods=['POST'])
def get_bigquery_solr():
    if request.method=='POST':
        jsonpost=dict(request.json)
        bibcodes = _bibcodespostget(jsonpost)
        d=perform_solr_bigquery(bibcodes)
        return jsonify(d)

if __name__ == "__main__":
    adsgut.run(host="0.0.0.0", port=4000)
