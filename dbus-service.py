from threading import Thread
import pwd

from gi.repository import GLib
from proto97.db import db, subtype_to_string
from proto97.sensor import cancel_capture, identify
from proto97.sid import sid_from_string
from proto97.tls import tls
from proto97.usb import usb
from prototype import open97
from pydbus import SystemBus
from pydbus.generic import signal

print("Starting up")

LOOP = GLib.MainLoop()

usb.quit = lambda e: LOOP.quit()

def uname2identity(uname):

    if uname == '':
        # For some reason Gnome enrollment UI does not send the user name
        # (it also ignores our num-enroll-stages attribute). I probably should upgrade Gnome
        raise Exception('No username specified')
    pw=pwd.getpwnam(uname)
    sidstr='S-1-5-21-111111111-1111111111-1111111111-%d' % pw.pw_uid
    return sid_from_string(sidstr)

class AlreadyInUse(Exception):
    __name__ = 'net.reactivated.Fprint.Error.AlreadyInUse'

class Device():
    name = 'Validity sensor'

    def __init__(self):
        setattr(self, 'num-enroll-stages', 7)
        setattr(self, 'scan-type', 'press')
        self.capturing = False
        self.user = None

    def Claim(self, user_name):
        print('In Claim %s' % user_name)
        self.claimed = user_name

    def Release(self):
        print('In Release')
        self.claimed = None

    def ListEnrolledFingers(self, usr):
        try:
            print('In ListEnrolledFingers %s' % usr)

            usr=db.lookup_user(uname2identity(usr))

            if usr == None:
                print('User not found on this device')
                return []

            rc = [subtype_to_string(f['subtype']) for f in usr.fingers]
            print(repr(rc))
            return rc
        except Exception as e:
            LOOP.quit()
            raise e

    def do_scan(self):
        if self.capturing:
            return

        try:
            self.capturing = True
            z=identify()
            self.VerifyStatus('verify-match', True)
        except Exception as e:
            self.VerifyStatus('verify-no-match', True)
            #LOOP.quit();
            raise e
        finally:
            self.capturing = False

    def VerifyStart(self, finger_name):
        print('In VerifyStart %s' % finger_name)
        Thread(target=lambda: self.do_scan()).start()
        #self.do_scan()

    def VerifyStop(self):
        print('In VerifyStop')
        cancel_capture()

    def DeleteEnrolledFingers(self, user):
        print('In DeleteEnrolledFingers %s' % user)
        usr=db.lookup_user(uname2identity(user))

        if usr == None:
            print('User not found on this device')
            return

        db.del_record(usr.dbid)

    def do_enroll(self, finger_name):
        # it is pointless to try and remember username passed in claim as Gnome does not seem to be passing anything useful anyway
        try:
            # hardcode the username and finger for now
            z=enroll(uname2identity(self.claimed), 0xf5)
            print('Enroll was successfull')
            self.EnrollStatus('enroll-completed', True)
        except Exception as e:
            self.EnrollStatus('enroll-failed', True)
            #LOOP.quit();
            raise e

    def EnrollStart(self, finger_name):
        print('In EnrollStart %s' % finger_name)
        Thread(target=lambda: self.do_enroll(finger_name)).start()


    def EnrollStop(self):
        print('In EnrollStop')

    VerifyFingerSelected = signal()
    VerifyStatus = signal()
    EnrollStatus = signal()

class Manager():
    def GetDevices(self):
        print('In GetDevices')
        return ['/net/reactivated/Fprint/Device/0']

    def GetDefaultDevice(self):
        print('In GetDefaultDevice')
        return '/net/reactivated/Fprint/Device/0'


def readif(fn):
    with open('/usr/share/dbus-1/interfaces/' + fn, 'rb') as f:
        # for some reason Gio can't seem to handle XML entities declared inline
        return f.read().decode('utf-8') \
                .replace('&ERROR_CLAIM_DEVICE;', 'net.reactivated.Fprint.Error.ClaimDevice') \
                .replace('&ERROR_ALREADY_IN_USE;', 'net.reactivated.Fprint.Error.AlreadyInUse') \
                .replace('&ERROR_INTERNAL;', 'net.reactivated.Fprint.Error.Internal') \
                .replace('&ERROR_PERMISSION_DENIED;', 'net.reactivated.Fprint.Error.PermissionDenied') \
                .replace('&ERROR_NO_ENROLLED_PRINTS;', 'net.reactivated.Fprint.Error.NoEnrolledPrints') \
                .replace('&ERROR_NO_ACTION_IN_PROGRESS;', 'net.reactivated.Fprint.Error.NoActionInProgress') \
                .replace('&ERROR_INVALID_FINGERNAME;', 'net.reactivated.Fprint.Error.InvalidFingername') \
                .replace('&ERROR_NO_SUCH_DEVICE;', 'net.reactivated.Fprint.Error.NoSuchDevice')


Device.dbus=[readif('net.reactivated.Fprint.Device.xml')]
Manager.dbus=[readif('net.reactivated.Fprint.Manager.xml')]


BUS = SystemBus()
BUS.publish(
    'net.reactivated.Fprint',
    ('/net/reactivated/Fprint/Manager', Manager()),
    ('/net/reactivated/Fprint/Device/0', Device())
)

open97()

usb.trace_enabled = False
tls.trace_enabled = False

LOOP.run()

print("Normal exit")
